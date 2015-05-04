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
import logging
from inspect import cleandoc
from time import sleep
from future.builtins import str

try:
    from pyvisa.highlevel import ResourceManager
    from pyvisa.rname import (assemble_canonical_name,
                              ASRLInstr, GPIBInstr, TCPIPInstr, TCPIPSocket)
    from pyvisa import constants
    from pyvisa import errors
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warn('The PyVISA library is necessary to use the visa backend')

from ..base_driver import BaseDriver
from ..util import byte_to_dict
from ..action import Action
from ..errors import InterfaceNotSupported, TimeoutError


_RESOURCE_MANAGER = None


def get_visa_resource_manager(backend='@ni'):
    """Access the VISA ressource manager in use by Eapii.

    """
    global _RESOURCE_MANAGER
    if not _RESOURCE_MANAGER or backend not in _RESOURCE_MANAGER:
        mess = cleandoc('''Creating default Visa resource manager for Lantz
            with backend {}.'''.format(backend))
        logging.debug(mess)
        if not _RESOURCE_MANAGER:
            _RESOURCE_MANAGER = {backend: ResourceManager(backend)}
        else:
            _RESOURCE_MANAGER[backend] = ResourceManager(backend)

    return _RESOURCE_MANAGER[backend]


def set_visa_resource_manager(rm, backend='@ni'):
    """Set the VISA ressource manager in use by Lantz.

    This operation can only be performed once, and should be performed
    before any driver relying on the visa protocol is created.

    Parameters
    ----------
    rm : RessourceManager
        Instance to use as Lantz default resource manager.

    """
    global _RESOURCE_MANAGER
    assert isinstance(rm, ResourceManager)
    if _RESOURCE_MANAGER and backend in _RESOURCE_MANAGER:
        msg = 'Cannot set Lantz VISA resource manager once one already exists.'
        raise ValueError(msg)

    if not _RESOURCE_MANAGER:
        _RESOURCE_MANAGER = {backend: rm}
    else:
        _RESOURCE_MANAGER[backend] = rm


class BaseVisaDriver(BaseDriver):
    """Base class for instrument communicating through the VISA protocol.

    It handles the connection management, but not the subsequent communication.
    That's why driver should not inherit from it but from one of its derived
    class (save for very peculiar use).

    Parameters
    ----------
    connection_infos : dict
        For a VisaInstrument you must provide either:
            - resource_name : the VISA id of your instrument. This should be
                              this should be reserved to the case of VISA
                              alias.

        or at least :
            - type : The kind of connection (GPIB, USB, PXI, ...).
            - address : The address of the instrument.

        In the second case other entries can be :
            - backend : the pyvisa backend to use ('@ni', '@sim', '@py')
            - any specifications concerning the connection (those depends on
              the type of connections, please see PyVisa documentation for
              more details).
            - para : a dict to alter the driver attributes.

        If some values are not provided the framework will give them default
        values to make sure that driver unicity is ensured.

    caching_allowed : bool, optional
        Boolean use to determine if instrument properties can be cached

    """
    #: Exceptions triggering a new communication attempts for Features with a
    #: non zero retries values.
    retries_exceptions = (TimeoutError, errors.VisaIOError)

    #: Protocols supported by the instrument.
    #: For example::
    #:
    #:       {'USB': ['RAW', 'INSTR'],
    #:        'TCPIP': '50000::SOCKET'}
    #:
    #: :type: dict[str, str | list]
    PROTOCOLS = None

    #: Default arguments passed to the Resource constructor on initialize.
    #: It should be specified in two layers, the first indicating the
    #: interface type and the second the corresponding arguments.
    #: The key COMMON is used to indicate keywords for all interfaces.
    #: For example::
    #:
    #:       {'ASRL':     {'read_termination': '\n',
    #:                     'baud_rate': 9600},
    #:        'USB':      {'read_termination': \r'},
    #:        'COMMON':   {'write_termination': '\n'}
    #:       }
    #:
    #: :type: dict[str, dict[str, str]]
    DEFAULTS = None

    def __init__(self, connection_infos, caching_allowed=True):
        super(BaseDriver, self).__init__(connection_infos, caching_allowed)

        # This entry is populated by the compute_id class method from the
        # provided informations.
        r_name = connection_infos['resource_name']

        rm = get_visa_resource_manager(connection_infos.get('backend', '@ni'))
        self._resource_manager = rm

        try:
            r_info = self._resource_manager.resource_info(r_name)
        except errors.VisaIOError:
            raise ValueError('The resource name is invalid')

        #: The resource name
        #: :type: str
        self.resource_name = r_name

        #: Keyword arguments passed to the resource during initialization.
        #: :type: dict
        kw = self._get_defaults_kwargs(r_info.interface_type.name.upper(),
                                       r_info.resource_class,
                                       connection_infos.get('para', {}))
        self.resource_kwargs = kw

        # The resource will be created when the driver is initialized.
        #: :type: pyvisa.resources.MessageBasedResource
        self._resource = None

    @classmethod
    def compute_id(cls, connection_infos):
        """Assemble the resource name from the provided infos.

        """
        if 'resource_name' not in connection_infos:
            connection_infos['resource_name'] =\
                assemble_canonical_name(**connection_infos)

        return connection_infos['resource_name']

    @classmethod
    def _get_defaults_kwargs(cls, instrument_type, resource_type,
                             **user_kwargs):
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
        instrument_type : str, {'ASRL', 'USB', 'TCPIP', 'GPIB', 'PXI'}
            Type of connection.

        resource_type : str, {'INSTR', 'SOCKET', 'RAW'}
            Type of ressource.

        Returns
        -------
        kwargs : dict
            The keyword arguments to use when opening a session.

        """
        if cls.DEFAULTS:

            kwargs = {}

            for key in ('COMMON', resource_type, instrument_type,
                        (instrument_type, resource_type)):
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
        sure the instrument queues do not keep corrupted data.

        """
        self.close_connection()
        self.open_connection()
        self._resource.clear()
        # Make sure the clear command completed before sending more commands.
        sleep(0.3)

    # --- Pyvisa wrappers

    @property
    def timeout(self):
        """The timeout in milliseconds for all resource I/O operations.

        None is mapped to VI_TMO_INFINITE.
        A value less than 1 is mapped to VI_TMO_IMMEDIATE.
        """
        return self._resource.timeout

    @timeout.setter
    def timeout(self, timeout):
        self._resource.timeout = timeout
        self.resource_kwargs['timeout'] = timeout

    @timeout.deleter
    def timeout(self):
        del self._resource.timeout
        del self.resource_kwargs.timeout

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
        """Clears this resource
        """
        self._resource.clear()

    def install_handler(self, event_type, handler, user_handle=None):
        """See Pyvisa docs.

        """
        return self._resource.install_handlers(event_type, handler,
                                               user_handle)

    def uninstall_handler(self, event_type, handler, user_handle=None):
        """See Pyvisa docs.

        """
        self._resource.uninstall_handler(self, event_type, handler,
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

    # TODO looks for standard meaning.
    @Action()
    def read_status_byte(self):
        return byte_to_dict(self._resource.read_stb(), range(8))

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
                 backend='@ni', caching_allowed=True, **kwargs):
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
        backend : {'@ni', '@sim', '@py'}
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

        query = 'USB{}::{}::{}::{}::{}'.format(board, manufacturer_id or '?*',
                                               model_code or '?*',
                                               serial_number or '?*',
                                               resource_type)

        rm = get_visa_resource_manager(backend)
        try:
            resource_names = rm.list_resources(query)
        except:
            raise ValueError('No USBTMC devices found for {}.'.format(query))

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

        return cls({'resource_name': resource_names[0], 'para': kwargs},
                   caching_allowed)

    @classmethod
    def via_usb(cls, serial_number=None, manufacturer_id=None,
                model_code=None, board=0, backend='@ni',
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
        backend : {'@ni', '@sim', '@py'}
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
                    model_code=None, board=0, backend='@ni',
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
        backend : {'@ni', '@sim', '@py'}
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
    def via_serial(cls, board, backend='@ni', caching_allowed=True, **kwargs):
        """Return a Driver with an underlying ASRL (Serial) Instrument resource.

        Parameters
        ----------
        port: int
            The serial port to which the instrument is connected.
        backend : {'@ni', '@sim', '@py'}
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
        return cls({'resource_name': str(resource_name), 'para': kwargs},
                   caching_allowed)

    @classmethod
    def via_tcpip(cls, host_address, lan_device_name='inst0', board=0,
                  backend='@ni', caching_allowed=True, **kwargs):
        """Return a Driver with an underlying TCP Instrument resource.

        Parameters
        ----------
        hostaddress : str
            The ip address or hostname of the instrument.
        hostname: str, optional
            Name of the instrument....
        board: int, optional
            The board number.
        backend : {'@ni', '@sim', '@py'}
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
        return cls({'resource_name': str(rname), 'para': kwargs},
                   caching_allowed)

    @classmethod
    def via_tcpip_socket(cls, host_address, port, board=0,
                         backend='@ni', caching_allowed=True, **kwargs):
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
        backend : {'@ni', '@sim', '@py'}
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
        return cls({'resource_name': str(rname), 'para': kwargs},
                   caching_allowed)

    @classmethod
    def via_gpib(cls, address, board=0, backend='@ni', caching_allowed=True,
                 **kwargs):
        """Return a Driver with an underlying GPIB Instrument resource.

        Parameters
        ----------
        address : int
             The gpib address of the instrument.
        board : int, optional
            Number of the GPIB board.
        backend : {'@ni', '@sim', '@py'}
            PyVISA backend to use.
        caching_allowed : bool
            Whether or not to allow caching for this specific driver instance.
        kwargs :
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """
        rname = GPIBInstr(board=board, address=address)
        return cls({'resource_name': str(rname), 'para': kwargs},
                   caching_allowed)

    # --- Pyvisa wrappers -----------------------------------------------------
    @property
    def encoding(self):
        """Encoding used for read and write operations.
        """
        return self._resource._encoding

    @encoding.setter
    def encoding(self, encoding):
        self._resource._encoding = encoding
        self.resource_kwargs['encoding'] = encoding

    @property
    def read_termination(self):
        """Read termination character.
        """
        return self._resource._read_termination

    @read_termination.setter
    def read_termination(self, value):
        self._resource._read_termination = value
        self.resource_kwargs['read_termination'] = value

    @property
    def write_termination(self):
        """Writer termination character.
        """
        return self._resource._write_termination

    @write_termination.setter
    def write_termination(self, value):
        self._resource._write_termination = value
        self.resource_kwargs['write_termination'] = value

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

    def write_values(self, message, values, termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self._resource.write_values(message, values, termination,
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
        return self._resource.query(message, delay)

    def query_values(self, message, delay=None):
        """See Pyvisa docs.

        """
        return self._resource.query_values(message, delay)

    def query_ascii_values(self, message, converter='f', separator=',',
                           container=list, delay=None):
        """See Pyvisa docs.

        """
        return self._resource.query_ascii_values(message, converter, separator,
                                                 container, delay)

    def query_binary_values(self, message, datatype='f', is_big_endian=False,
                            container=list, delay=None, header_fmt='ieee'):
        """See Pyvisa docs.

        """
        return self._resource.query_binary_values(message, datatype,
                                                  is_big_endian, container,
                                                  delay, header_fmt)

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
