# -*- coding: utf-8 -*-
"""
    lantz_core.backends.visa
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Module importing the pyvisa module components and implementing the base
    drivers for instrument communicating through the VISA protocol.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import os
import logging
from inspect import cleandoc
from time import sleep
from future.builtins import str
from future.utils import raise_with_traceback

try:
    from pyvisa.highlevel import ResourceManager
    from pyvisa.rname import (assemble_canonical_name, to_canonical_name,
                              ASRLInstr, GPIBInstr, TCPIPInstr, TCPIPSocket)
    from pyvisa import constants
    from pyvisa import errors
except ImportError:
    msg = 'The PyVISA library is necessary to use the visa backend.'
    raise_with_traceback(ImportError(msg))

from ..base_driver import BaseDriver
from ..util import byte_to_dict
from ..action import Action
from ..errors import InterfaceNotSupported, TimeoutError


_RESOURCE_MANAGERS = None


def get_visa_resource_manager(backend='default'):
    """Access a VISA ressource manager in use by Lantz.

    """
    global _RESOURCE_MANAGERS
    if not _RESOURCE_MANAGERS:
        _RESOURCE_MANAGERS = {}

    if backend not in _RESOURCE_MANAGERS:

        if backend == 'default':
            def_backend = os.environ.get('LANTZ_VISA', '@ni')
            mess = cleandoc('''Creating default Visa resource manager for Lantz
                with backend {}.'''.format(def_backend))
            logging.debug(mess)
            _RESOURCE_MANAGERS[backend] = ResourceManager(def_backend)

        elif '@' in backend:
            _RESOURCE_MANAGERS[backend] = ResourceManager(backend)

    return _RESOURCE_MANAGERS[backend]


def set_visa_resource_manager(rm, backend='default'):
    """Set a VISA ressource manager in use by Lantz.

    This operation can only be performed once per backend id, and should be
    performed before any driver relying on this backend is created..

    Parameters
    ----------
    rm : ResourceManager
        Instance to use as Lantz resource manager.

    backend : unicode
        Id of the backend.

    """
    global _RESOURCE_MANAGERS
    assert isinstance(rm, ResourceManager)
    if _RESOURCE_MANAGERS and backend in _RESOURCE_MANAGERS:
        msg = 'Cannot set Lantz VISA resource manager once one already exists.'
        raise ValueError(msg)

    if not _RESOURCE_MANAGERS:
        _RESOURCE_MANAGERS = {backend: rm}
    else:
        _RESOURCE_MANAGERS[backend] = rm


class PyvisaProperty(property):
    """Special property used to wrap a property present in a Pyvisa resource.

    """

    def __init__(self, name, deleter=None):
        super(PyvisaProperty, self).__init__(self._get, self._set, deleter)

        self.name = name

    def _get(self, obj):
        if obj._resource:
            return getattr(obj._resource, self.name)
        else:
            return obj.resource_kwargs.get(self.name)

    def _set(self, obj, value):
        obj.resource_kwargs[self.name] = value
        if obj._resource:
            setattr(obj._resource, self.name, value)


def timeout_deleter(obj):
    del obj.resource_kwargs['timeout']
    if obj._resource:
        del obj._resource.timeout


class BaseVisaDriver(BaseDriver):
    """Base class for instrument communicating through the VISA protocol.

    It handles the connection management, but not the subsequent communication.
    That's why driver should not inherit from it but from one of its derived
    class (save for very peculiar use).

    Parameters
    ----------
    resource_name : unicode, optional
        Name of the visa resource. can be specified as positional argument.

    backend : unicode, optional
        The pyvisa backend to use. This can either be a backend alias declared
        using set_visa_resource_manager or a valid string to create a pyvisa
        resource maanger.

    parameters : dict, optionalm
        A dict to alter the driver attributes.

    caching_allowed : bool, optional
        Boolean use to determine if instrument properties can be cached

    kwargs :
        Arguments that PyVISA can use to build a resource name. Those depend
        on the interface type (*interface_type* keyword), please see PyVisa
        documentation for ore details.

    """
    #: Exceptions triggering a new communication attempts for Features with a
    #: non zero retries values.
    retries_exceptions = (TimeoutError, errors.VisaIOError)

    #: Protocols supported by the instrument.
    #: For each type of interface a dictionary (or a list of dictionary),
    #: specifying the default arguments to use should be provided.
    #: For example::
    #:
    #:       {'USB': [{'resource_class': 'INSTR'},
    #:                {'resource_class': 'RAW'}],
    #:        'TCPIP': {'resource_class': 'SOCKET',
    #:                  'port': '50000'}
    PROTOCOLS = {}

    #: Default arguments passed to the Resource constructor on initialize.
    #: It should be specified in two layers, the first indicating the
    #: interface type and the second the corresponding arguments.
    #: The key COMMON is used to indicate keywords for all interfaces.
    #: For example:
    #:
    #:       {'ASRL':     {'read_termination': '\n',
    #:                     'baud_rate': 9600},
    #:        'USB':      {'read_termination': \r'},
    #:        'COMMON':   {'write_termination': '\n'}
    #:       }
    DEFAULTS = None

    #: Tuple of keywords unrelated to Visa resource name. Used to remove them
    #: from the kwargs when building the resource name.
    NON_VISA_NAMES = ('parameters', 'backend')

    def __init__(self, *args, **kwargs):
        super(BaseVisaDriver, self).__init__(*args, **kwargs)

        # This entry is populated by the compute_id class method (called by the
        # the metaclass) from the provided informations.
        r_name = kwargs['resource_name']

        rm = get_visa_resource_manager(kwargs.get('backend', 'default'))
        self._resource_manager = rm

        # Does not work with Visa alias
        r_info = self._resource_manager.resource_info(r_name)
        if r_info:
            #: Keyword arguments passed to the resource during initialization.
            kw = self._get_defaults_kwargs(r_info.interface_type.name.upper(),
                                           r_info.resource_class,
                                           kwargs.get('parameters', {}))
            self.resource_kwargs = kw
        else:
            # Allow to at least get the COMMON parameters.
            kw = self._get_defaults_kwargs(None,
                                           None,
                                           kwargs.get('parameters', {}))
            self.resource_kwargs = kw

        #: The resource name
        self.resource_name = r_name

        # The resource will be created when the driver is initialized.
        self._resource = None

    @classmethod
    def compute_id(cls, args, kwargs):
        """Assemble the resource name from the provided infos.

        """
        rname = None
        if args:
            msg = 'A single positional argument is allowed for %s' % cls
            assert len(args) == 1, msg
            rname = args[0]
        elif 'resource_name' in kwargs:
            rname = kwargs['resource_name']

        if rname:
            try:
                kwargs['resource_name'] = to_canonical_name(rname)
            except Exception:  # TODO Use a more adequate exception
                # Fail silently to allow the use of VISA alias
                kwargs['resource_name'] = rname
        else:
            visa_infos = cls._get_visa_infos(kwargs)
            kwargs['resource_name'] =\
                assemble_canonical_name(**visa_infos)

        return kwargs['resource_name']

    @classmethod
    def _get_visa_infos(cls, connection_infos):
        """Filter out non-VISA related keywords and fill the gaps using
        PROTOCOLS

        """
        interface_type = connection_infos['interface_type']
        default_protocol = cls.PROTOCOLS.get(interface_type, {})
        if not isinstance(default_protocol, dict):
            default_protocol = default_protocol[0]

        visa_infos = {k: v for k, v in connection_infos.items()
                      if k not in cls.NON_VISA_NAMES}

        default_protocol.update(visa_infos)
        return default_protocol

    @classmethod
    def _get_defaults_kwargs(cls, interface_type, resource_class,
                             user_kwargs):
        """Compute the default keyword arguments.

        This is done by combining:
            - user provided keyword arguments.
            - (instrument_type, resource_type) keyword arguments.
            - instrument_type keyword arguments.
            - resource_type keyword arguments.
            - common keyword arguments.

        (the first ones have precedence)

        Parameters
        ----------
        interface_type : str|None, {'ASRL', 'USB', 'TCPIP', 'GPIB', 'PXI'}
            Type of interface.

        resource_class : str|None, {'INSTR', 'SOCKET', 'RAW'}
            Class of ressource.

        Returns
        -------
        kwargs : dict
            The keyword arguments to use when opening a session.

        """
        if cls.DEFAULTS:

            kwargs = {}

            for key in ('COMMON', resource_class, interface_type,
                        (interface_type, resource_class)):
                if key not in cls.DEFAULTS:
                    continue
                value = cls.DEFAULTS[key]
                if value is None:
                    msg = 'An %s instrument is not supported by the driver %s'
                    raise InterfaceNotSupported(msg, key, cls.__name__)
                if value:
                    kwargs.update(value)

            if user_kwargs:
                kwargs.update(user_kwargs)

            return kwargs
        else:
            return user_kwargs

    def initialize(self):
        rm = self._resource_manager
        self._resource = rm.open_resource(self.resource_name,
                                          **self.resource_kwargs)

    def finalize(self):
        self._resource.close()
        self._resource = None

    def reopen_connection(self):
        """Close and re-open a suspicious connection.

        A VISA clear command is issued after re-opening the connection to make
        sure the instrument queues do not keep corrupted data. This might be
        an issue with some instruments in such a case simply override this
        method.

        """
        self.finalize()
        self.initialize()
        self._resource.clear()
        # Make sure the clear command completed before sending more commands.
        sleep(0.3)

    # --- Pyvisa wrappers

    #: The timeout in milliseconds for all resource I/O operations.
    #:
    #: None is mapped to VI_TMO_INFINITE.
    #: A value less than 1 is mapped to VI_TMO_IMMEDIATE.
    timeout = PyvisaProperty('timeout', timeout_deleter)

    @property
    def resource_info(self):
        """See Pyvisa docs.

        """
        return self._resource.resource_info

    @property
    def interface_type(self):
        """See Pyvisa docs.

        """
        return self._resource.interface_type

    def clear(self):
        """Clears this resource.

        """
        self._resource.clear()

    def install_handler(self, event_type, handler, user_handle=None):
        """See Pyvisa docs.

        """
        return self._resource.install_handler(event_type, handler,
                                              user_handle)

    def uninstall_handler(self, event_type, handler, user_handle=None):
        """See Pyvisa docs.

        """
        self._resource.uninstall_handler(event_type, handler,
                                         user_handle)


class VisaMessageDriver(BaseVisaDriver):
    """Base class for driver communicating using VISA through text based
    messages.

    This covers among others GPIB, USB, TCPIP in INSTR mode, TCPIP in SOCKET
    mode.

    """
    #: The identification number of the manufacturer as hex code.
    #: :type: str | None
    MANUFACTURER_ID = None

    #: The code number of the model as hex code.
    #: Can provide a tuple/list to indicate multiple models.
    #: :type: str | list | tuple | None
    MODEL_CODE = None

    #: Meaning of the status byte.
    STATUS_BYTE = (0,
                   1,
                   2,
                   3,
                   'Message available',
                   'Event status',
                   'Request',
                   7)

    @Action()
    def read_status_byte(self):
        return byte_to_dict(self._resource.read_stb(), self.STATUS_BYTE)

    def default_get_feature(self, iprop, cmd, *args, **kwargs):
        """Query the value using the provided command.

        The command is formatted using the provided args and kwargs before
        being passed on to the instrument.

        """
        return self._resource.query(cmd.format(*args, **kwargs))

    def default_set_feature(self, iprop, cmd, *args, **kwargs):
        """Set the iproperty value of the instrument.

        The command is formatted using the provided args and kwargs before
        being passed on to the instrument.

        """
        return self._resource.write(cmd.format(*args, **kwargs))

    @classmethod
    def _via_usb(cls, resource_type='INSTR', serial_number=None,
                 manufacturer_id=None, model_code=None, board=0,
                 backend='default', caching_allowed=True, **kwargs):
        """Return a Driver with an underlying USB resource.

        A connected USBTMC instrument with the specified serial_number,
        manufacturer_id, and model_code is returned. If any of these is
        missing, the first USBTMC driver matching any of the provided values is
        returned.

        To specify the manufacturer id and/or the model code override the
        following class attributes::

            class RigolDS1052E(VisaMessageDriver):

                MANUFACTURER_ID = '0x1AB1'
                MODEL_CODE = '0x0588'

        Parameters
        ----------
        serial_number : str
            The serial number of the instrument.
        manufacturer_id : str
            The unique identification number of the manufacturer.
        model_code: str
            The unique identification number of the product.
        board: int
            USB Board to use.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """

        manufacturer_id = manufacturer_id or cls.MANUFACTURER_ID
        model_code = model_code or cls.MODEL_CODE

        if isinstance(model_code, (list, tuple)):
            _models = model_code
            model_code = '?*'
        else:
            _models = None

        query = 'USB{}::{}::{}::{}::?*::{}'.format(board,
                                                   manufacturer_id or '?*',
                                                   model_code or '?*',
                                                   serial_number or '?*',
                                                   resource_type)

        rm = get_visa_resource_manager(backend)
        try:
            resource_names = rm.list_resources(query)
        except errors.VisaIOError:
            msg = 'No USBTMC devices found for {}.'.format(query)
            raise_with_traceback(ValueError(msg))

        if _models:
            # There are more than 1 model compatible with
            resource_names = [r for r in resource_names
                              if r.split('::')[2] in _models]

        if not resource_names:
            msg = 'No USBTMC devices found for {} with model in {}'
            raise ValueError(msg.format(query, _models))

        if len(resource_names) > 1:
            msg = cleandoc('''{} USBTMC devices found for {}. Please specify
                           the serial number''')
            raise ValueError(msg.format(len(resource_names), query))

        return cls(resource_names[0], parameters=kwargs,
                   backend=backend, caching_allowed=caching_allowed)

    @classmethod
    def via_usb(cls, serial_number=None, manufacturer_id=None,
                model_code=None, board=0, backend='default',
                caching_allowed=True, **kwargs):
        """Return a Driver with an underlying USB Instrument resource.

        A connected USBTMC instrument with the specified serial_number,
        manufacturer_id, and model_code is returned. If any of these is
        missing, the first USBTMC driver matching any of the provided values is
        returned.

        To specify the manufacturer id and/or the model code override the
        following class attributes::

            class RigolDS1052E(VisaMessageDriver):

                MANUFACTURER_ID = '0x1AB1'
                MODEL_CODE = '0x0588'

        Parameters
        ----------
        serial_number : str
            The serial number of the instrument.
        manufacturer_id : str
            The unique identification number of the manufacturer.
        model_code: str
            The unique identification number of the product.
        board: int
            USB Board to use.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """

        return cls._via_usb('INSTR', serial_number, manufacturer_id,
                            model_code, board, backend, caching_allowed,
                            **kwargs)

    @classmethod
    def via_usb_raw(cls, serial_number=None, manufacturer_id=None,
                    model_code=None, board=0, backend='default',
                    caching_allowed=True,  **kwargs):
        """Return a Driver with an underlying USB RAW resource.

        Parameters
        ----------
        serial_number : str
            The serial number of the instrument.
        manufacturer_id : str
            The unique identification number of the manufacturer.
        model_code: str
            The unique identification number of the product.
        board: int
            USB Board to use.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """

        return cls._via_usb('RAW', serial_number, manufacturer_id, model_code,
                            board, backend, caching_allowed, **kwargs)

    @classmethod
    def via_serial(cls, board, backend='default', caching_allowed=True,
                   **kwargs):
        """Return a Driver with an underlying ASRL (Serial) Instrument resource.

        Parameters
        ----------
        port: int
            The serial port to which the instrument is connected.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """
        resource_name = ASRLInstr(board=board)
        return cls(str(resource_name), parameters=kwargs, backend=backend,
                   caching_allowed=caching_allowed)

    @classmethod
    def via_tcpip(cls, host_address, lan_device_name='inst0', board=0,
                  backend='default', caching_allowed=True, **kwargs):
        """Return a Driver with an underlying TCP Instrument resource.

        Parameters
        ----------
        hostaddress : str
            The ip address or hostname of the instrument.
        hostname: str, optional
            Name of the instrument....
        board: int, optional
            The board number.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver: VisaMessageDriver

        """
        rname = TCPIPInstr(**{'host_address': host_address,
                              'lan_device_name': lan_device_name,
                              'board': board})
        return cls(str(rname), parameters=kwargs, backend=backend,
                   caching_allowed=caching_allowed)

    @classmethod
    def via_tcpip_socket(cls, host_address, port, board=0,
                         backend='default', caching_allowed=True, **kwargs):
        """Return a Driver with an underlying TCP Socket resource.

        Parameters
        ----------
        hostaddress : str
            The ip address or hostname of the instrument.
        hostname: str, optional
            Name of the instrument....
        port : int
            The port of the instrument.
        board: int, optional
            The board number.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """
        rname = TCPIPSocket(**{'host_address': host_address,
                               'port': port,
                               'board': board})
        return cls(str(rname), parameters=kwargs, backend=backend,
                   caching_allowed=caching_allowed)

    @classmethod
    def via_gpib(cls, address, board=0, backend='default',
                 caching_allowed=True,
                 **kwargs):
        """Return a Driver with an underlying GPIB Instrument resource.

        Parameters
        ----------
        address : int
             The gpib address of the instrument.
        board : int, optional
            Number of the GPIB board.
        backend :
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs :
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """
        rname = GPIBInstr(board=board, primary_address=address)
        return cls(str(rname), parameters=kwargs, backend=backend,
                   caching_allowed=caching_allowed)

    # --- Pyvisa wrappers -----------------------------------------------------

    #: Encoding used for read and write operations.
    encoding = PyvisaProperty('encoding')

    #: Read termination character.
    read_termination = PyvisaProperty('read_termination')

    #: Write termination character.
    write_termination = PyvisaProperty('write_termination')

    def write_raw(self, message):
        """See Pyvisa docs.

        """
        return self._resource.write_raw(message)

    def write(self, message, termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self._resource.write(message, termination, encoding)

    def write_ascii_values(self, message, values, converter='f', separator=',',
                           termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self._resource.write_ascii_values(message, values, converter,
                                                 separator, termination,
                                                 encoding)

    def write_binary_values(self, message, values, datatype='f',
                            is_big_endian=False, termination=None,
                            encoding=None):
        """See Pyvisa docs.

        """
        return self._resource.write_binary_values(message, values, datatype,
                                                  is_big_endian, termination,
                                                  encoding)

    def read_raw(self, size=None):
        """See Pyvisa docs.

        """
        return self._resource.read_raw(size)

    def read(self, termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self._resource.read(termination, encoding)

    def read_values(self, fmt=None, container=list):
        """See Pyvisa docs.

        """
        return self._resource.read_values(fmt, container)

    def query(self, message, delay=None):
        """See Pyvisa docs.

        """
        with self.lock:
            return self._resource.query(message, delay)

    def query_ascii_values(self, message, converter='f', separator=',',
                           container=list, delay=None):
        """See Pyvisa docs.

        """
        with self.lock:
            return self._resource.query_ascii_values(message, converter,
                                                     separator, container,
                                                     delay)

    def query_binary_values(self, message, datatype='f', is_big_endian=False,
                            container=list, delay=None, header_fmt='ieee'):
        """See Pyvisa docs.

        """
        with self.lock:
            return self._resource.query_binary_values(message, datatype,
                                                      is_big_endian, container,
                                                      delay, header_fmt)

    @Action()
    def assert_trigger(self):
        """Sends a software trigger to the device.

        """
        self._resource.assert_trigger()


class VisaRegisterDriver(BaseVisaDriver):
    """Base class for driver based on VISA and a binary registry.

    This covers among others PXI, ...

    """
    def read_memory(self, space, offset, width, extended=False):
        """See Pyvisa docs.

        """
        return self._resource.read_memory(space, offset, width, extended)

    def write_memory(self, space, offset, data, width, extended=False):
        """See Pyvisa docs.

        """
        return self._resource.write_memory(space, offset, data, width,
                                           extended)

    def move_in(self, space, offset, length, width, extended=False):
        """See Pyvisa docs.

        """
        return self._resource.move_in(space, offset, length, width, extended)

    def move_out(self, space, offset, length, data, width, extended=False):
        """See Pyvisa docs.

        """
        return self._resource.move_out(space, offset, length, data, width,
                                       extended)
