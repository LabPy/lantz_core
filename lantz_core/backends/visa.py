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
import types
from inspect import cleandoc
from collections import ChainMap
from time import sleep

from pyvisa.highlevel import ResourceManager
from pyvisa.errors import VisaIOError, VisaTypeError
from pyvisa import constants


from ..features.register import Register
from ..baseresources import BaseInstrument
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
    if _RESOURCE_MANAGER and backend in _RESOURCE_MANAGER:
        mess = 'Cannot set Eapii resource manager once one already exists.'
        raise ValueError(mess)

    if not _RESOURCE_MANAGER:
        _RESOURCE_MANAGER = {backend: rm}
    else:
        _RESOURCE_MANAGER[backend] = rm


class BaseVisaInstrument(BaseInstrument):
    """Base class for instrument communicating through the VISA protocol.

    It handles the connection management, but not the subsequent communication.
    That's why driver should not inherit from it but from one of its derived
    class (save for very peculiar use).

    Parameters
    ----------
    connection_infos : dict
        For a VisaInstrument two entries at least are expected:
            - type : The kind of connection (GPIB, USB, PXI, ...). The board
                     number can be specified too. NB: for serial (ASRL) do not
                     specify the board use the address entry instead.
            - address : The address of the instrument.

        Other entries can be :
            - mode : Mode of connection (INSTR, RAW, SOCKET). If absent INSTR
                     will be assumed.
            - para : a dict to alter the driver attributes.

        Those information will be concatenated using ::.

    caching_allowed : bool, optional
        Boolean use to determine if instrument properties can be cached
    caching_permissions : dict(str : bool), optionnal
        Dict specifying which instrument properties can be cached, override the
        default parameters specified in the class attribute.
    auto_open : bool, optional
        Whether to automatically open the connection to the instrument when the
        driver is instantiated.

    Attributes
    ----------
    protocols : dict
        Class attributes used for introspection purposes, it should specify
        the kind of connection supported by the instrument (GPIB, USB, ...) and
        the mode (INSTR, port::SOCKET, ...)

    """
    retries_exceptions = (TimeoutError, VisaIOError)

    protocols = {}

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

    #: The identification number of the manufacturer as hex code.
    #: :type: str | None
    MANUFACTURER_ID = None

    #: The code number of the model as hex code.
    #: Can provide a tuple/list to indicate multiple models.
    #: :type: str | list | tuple | None
    MODEL_CODE = None

    #: Stores a reference to a PyVISA ResourceManager.
    #: :type: visa.ResourceManager
    __resource_manager = None

    @classmethod
    def _get_defaults_kwargs(cls, instrument_type, resource_type,
                             **user_kwargs):
        """Compute the default keyword arguments combining:
            - user provided keyword arguments.
            - (instrument_type, resource_type) keyword arguments.
            - instrument_type keyword arguments.
            - resource_type keyword arguments.
            - common keyword arguments.

        (the first ones have precedence)

        :param instrument_type: ASRL, USB, TCPIP, GPIB
        :type instrument_type: str
        :param resource_type: INSTR, SOCKET, RAW
        :type resource_type: str

        :rtype: dict
        """

        if cls.DEFAULTS:

            maps = [user_kwargs] if user_kwargs else []

            for key in ((instrument_type, resource_type), instrument_type,
                        resource_type, 'COMMON'):
                if key not in cls.DEFAULTS:
                    continue
                value = cls.DEFAULTS[key]
                if value is None:
                    msg = 'An %s instrument is not supported by the driver %s'
                    raise InterfaceNotSupported(msg, key, cls.__name__)
                if value:
                    maps.append(value)

            return dict(ChainMap(*maps))
        else:
            return user_kwargs

    @classmethod
    def _via_usb(cls, resource_type='INSTR', serial_number=None,
                 manufacturer_id=None, model_code=None, name=None, board=0,
                 **kwargs):
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
        name:
            Unique name given within Lantz to the instrument for logging
            purposes. Defaults to one generated based on the class name if not
            provided.
        board: int
            USB Board to use.
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

        query = 'USB%d::%s::%s::%s::%s' % (board, manufacturer_id or '?*',
                                           model_code or '?*',
                                           serial_number or '?*',
                                           resource_type)

        rm = get_resource_manager()
        try:
            resource_names = rm.list_resources(query)
        except:
            raise ValueError('No USBTMC devices found for %s' % query)

        if _models:
            # There are more than 1 model compatible with
            resource_names = [r for r in resource_names
                              if r.split('::')[2] in _models]

            if not resource_names:
                raise ValueError('No USBTMC devices found for %s '
                                 'with model in %s' % (query, _models))

        if len(resource_names) > 1:
            raise ValueError('%d USBTMC devices found for %s. '
                             'Please specify the serial number' % (len(resource_names), query))

        return cls(resource_names[0], name, **kwargs)

    @classmethod
    def via_usb(cls, serial_number=None, manufacturer_id=None,
                model_code=None, name=None, board=0, **kwargs):
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
        name:
            Unique name given within Lantz to the instrument for logging
            purposes. Defaults to one generated based on the class name if not
            provided.
        board: int
            USB Board to use.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
            driver : VisaMessageDriver

        """

        return cls._via_usb('INSTR', serial_number, manufacturer_id,
                            model_code, name, board, **kwargs)

    @classmethod
    def via_usb_raw(cls, serial_number=None, manufacturer_id=None,
                    model_code=None, name=None, board=0, **kwargs):
        """Return a Driver with an underlying USB RAW resource.

        Parameters
        ----------
        serial_number : str
            The serial number of the instrument.
        manufacturer_id : str
            The unique identification number of the manufacturer.
        model_code: str
            The unique identification number of the product.
        name:
            Unique name given within Lantz to the instrument for logging
            purposes. Defaults to one generated based on the class name if not
            provided.
        board: int
            USB Board to use.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
            driver : VisaMessageDriver

        """

        return cls._via_usb('RAW', serial_number, manufacturer_id, model_code,
                            name, board, **kwargs)

    @classmethod
    def via_serial(cls, port, name=None, **kwargs):
        """Return a Driver with an underlying ASRL (Serial) Instrument resource.

        Parameters
        ----------
        port: int
            The serial port to which the instrument is connected.
        name: str
            Unique name given within Lantz to the instrument for logging
            purposes. Defaults to one generated based on the class name if not
            provided.
        kwargs:
            keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """
        resource_name = 'ASRL%s::INSTR' % port
        return cls(resource_name, name, **kwargs)

    @classmethod
    def via_tcpip(cls, hostaddress, hostname='', board=0, name=None, **kwargs):
        """Return a Driver with an underlying TCP Instrument resource.

        Parameters
        ----------
        hostaddress : str
            The ip address or hostname of the instrument.
        hostname: str, optional
            Name of the instrument....
        board: int, optional
            The board number.
        name: str, optional
            Unique name given within Lantz to the instrument for logging
            purposes. Defaults to one generated based on the class name if not
            provided.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver: VisaMessageDriver

        """
        if hostname:
            re_str = 'TCPIP%s::%s::%s::INSTR'
            resource_name = re_str % (board, hostaddress, hostname)
        else:
            re_str = 'TCPIP%s::%s::INSTR'
            resource_name = re_str % (board, hostaddress)
        return cls(resource_name, name, **kwargs)

    @classmethod
    def via_tcpip_socket(cls, hostaddress, port, hostname='', board=0,
                         name=None, **kwargs):
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
        name: str, optional
            Unique name given within Lantz to the instrument for logging
            purposes. Defaults to one generated based on the class name if not
            provided.
        kwargs:
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """
        if hostname:
            re_str = 'TCPIP%s::%s::%s::%s::SOCKET'
            resource_name = re_str % (board, hostaddress, hostname, port)
        else:
            re_str = 'TCPIP%s::%s::%s::SOCKET'
            resource_name = re_str % (board, hostaddress)
        return cls(resource_name, name, **kwargs)

    @classmethod
    def via_gpib(cls, address, board=0, name=None, **kwargs):
        """Return a Driver with an underlying GPIB Instrument resource.

        Parameters
        ----------
        address : int
             The gpib address of the instrument.
        board : int, optional
            Number of the GPIB board.
        name : str, optional
            Unique name given within Lantz to the instrument for logging
            purposes. Defaults to one generated based on the class name if not
            provided.
        kwargs :
            Keyword arguments passed to the Resource constructor on initialize.

        Returns
        -------
        driver : VisaMessageDriver

        """
        resource_name = 'GPIB::%s::INSTR' % address
        return cls(resource_name, name, **kwargs)

    def __init__(self, resource_name, name=None, **kwargs):
        """
        :param resource_name: The resource name
        :type resource_name: str
        :params name: easy to remember identifier given to the instance for logging
                      purposes.
        :param kwargs: keyword arguments passed to the resource during initialization.
        """

        self.__resource_manager = get_resource_manager()
        try:
            resource_info = self.__resource_manager.resource_info(resource_name)
        except visa.VisaIOError:
            raise ValueError('The resource name is invalid')

        super().__init__(name=name)

        # This is to avoid accidental modifications of the class value by an instance.
        self.DEFAULTS = types.MappingProxyType(self.DEFAULTS or {})

        #: The resource name
        #: :type: str
        self.resource_name = resource_name

        #: keyword arguments passed to the resource during initialization.
        #: :type: dict
        self.resource_kwargs = self._get_defaults_kwargs(resource_info.interface_type.name.upper(),
                                                         resource_info.resource_class,
                                                         **kwargs)

        # The resource will be created when the driver is initialized.
        #: :type: pyvisa.resources.MessageBasedResource
        self.resource = None

        self.log_debug('Using MessageBasedDriver for {}', self.resource_name)

    def __init__(self, connection_infos, caching_allowed=True,
                 caching_permissions={}, auto_open=True):
        super(BaseVisaInstrument, self).__init__(connection_infos,
                                                 caching_allowed,
                                                 caching_permissions,
                                                 auto_open)

        self.connection_str = str(connection_infos['type']
                                  + '::' + connection_infos['address']
                                  + '::' + connection_infos['mode'])
        self.resource = None
        self._para = connection_infos.get('para', {})
        if auto_open:
            self.open_connection()

    @classmethod
    def compute_id(cls, connection_infos):
        """Insert the default mode in the connection_infos to avoid ambiguity
        in the id.

        """
        if not connection_infos.get('mode'):
            connection_infos['mode'] = 'INSTR'

        super(BaseVisaInstrument, cls).compute_id(connection_infos)

    def initialize(self):
        rm = get_visa_resource_manager(self.backend)
        self.resource = rm.open_resource(self.connection_str, **self._para)

    def finalize(self):
        self.resource.close()
        self.resource = None

    def reopen_connection(self):
        """Close and re-open a suspicious connection.

        A VISA clear command is issued after re-opening the connection to make
        sure the instrument queues do not keep corrupted data.

        """
        self.close_connection()
        self.open_connection()
        self.resource.clear()
        # Make sure the clear command completed before sending more commands.
        sleep(0.3)

    # --- Pyvisa wrappers

    @property
    def timeout(self):
        """The timeout in milliseconds for all resource I/O operations.

        None is mapped to VI_TMO_INFINITE.
        A value less than 1 is mapped to VI_TMO_IMMEDIATE.
        """
        return self.resource.timeout

    @timeout.setter
    def timeout(self, timeout):
        self.resource.timeout = timeout
        self._para['timeout'] = timeout

    @timeout.deleter
    def timeout(self):
        del self.resource.timeout
        del self._para.timeout

    @property
    def resource_info(self):
        """See Pyvisa docs.

        """
        return self.resource.resource_info

    @property
    def interface_type(self):
        """See Pyvisa docs.

        """
        return self.resource.interface_type

    def clear(self):
        """Clears this resource
        """
        self.resource.clear()

    def install_handler(self, event_type, handler, user_handle=None):
        """See Pyvisa docs.

        """
        return self.resource.install_handlers(event_type, handler, user_handle)

    def uninstall_handler(self, event_type, handler, user_handle=None):
        """See Pyvisa docs.

        """
        self.resource.uninstall_handler(self, event_type, handler, user_handle)


class VisaMessageInstrument(BaseVisaInstrument):
    """Base class for driver communicating using VISA through text based
    messages.

    This covers among others GPIB, USB, TCPIP in INSTR mode, TCPIP in SOCKET
    mode.

    """
    #: Status byte of the instrument.
    status_byte = Register(getter=True, names=[None]*8)

    def default_get_iproperty(self, iprop, cmd, *args, **kwargs):
        """Query the value using the provided command.

        The command is formatted using the provided args and kwargs before
        being passed on to the instrument.

        """
        return self.resource.query(cmd.format(*args, **kwargs))

    def default_set_iproperty(self, iprop, cmd, *args, **kwargs):
        """Set the iproperty value of the instrument.

        The command is formatted using the provided args and kwargs before
        being passed on to the instrument.

        """
        self.resource.write(cmd.format(*args, **kwargs))

    # --- Pyvisa wrappers -----------------------------------------------------
    @property
    def encoding(self):
        """Encoding used for read and write operations.
        """
        return self.resource._encoding

    @encoding.setter
    def encoding(self, encoding):
        self.resource._encoding = encoding
        self._para['encoding'] = encoding

    @property
    def read_termination(self):
        """Read termination character.
        """
        return self.resource._read_termination

    @read_termination.setter
    def read_termination(self, value):
        self.resource._read_termination = value
        self._para['read_termination'] = value

    @property
    def write_termination(self):
        """Writer termination character.
        """
        return self.resource._write_termination

    @write_termination.setter
    def write_termination(self, value):
        self.resource._write_termination = value
        self._para['write_termination'] = value

    def write_raw(self, message):
        """See Pyvisa docs.

        """
        return self.resource.write_raw(message)

    def write(self, message, termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self.resource.write(message, termination, encoding)

    def write_ascii_values(self, message, values, converter='f', separator=',',
                           termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self.resource.write_ascii_values(message, values, converter,
                                                separator, termination,
                                                encoding)

    def write_binary_values(self, message, values, datatype='f',
                            is_big_endian=False, termination=None,
                            encoding=None):
        """See Pyvisa docs.

        """
        return self.resource.write_binary_values(message, values, datatype,
                                                 is_big_endian, termination,
                                                 encoding)

    def write_values(self, message, values, termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self.resource.write_values(message, values, termination,
                                          encoding)

    def read_raw(self, size=None):
        """See Pyvisa docs.

        """
        return self.resource.read_raw(size)

    def read(self, termination=None, encoding=None):
        """See Pyvisa docs.

        """
        return self.resource.read(termination, encoding)

    def read_values(self, fmt=None, container=list):
        """See Pyvisa docs.

        """
        return self.resource.read_values(fmt, container)

    def query(self, message, delay=None):
        """See Pyvisa docs.

        """
        return self.resource.query(message, delay)

    def query_values(self, message, delay=None):
        """See Pyvisa docs.

        """
        return self.resource.query_values(message, delay)

    def query_ascii_values(self, message, converter='f', separator=',',
                           container=list, delay=None):
        """See Pyvisa docs.

        """
        return self.resource.query_ascii_values(message, converter, separator,
                                                container, delay)

    def query_binary_values(self, message, datatype='f', is_big_endian=False,
                            container=list, delay=None, header_fmt='ieee'):
        """See Pyvisa docs.

        """
        return self.resource.query_binary_values(message, datatype,
                                                 is_big_endian, container,
                                                 delay, header_fmt)

    def assert_trigger(self):
        """Sends a software trigger to the device.

        """
        self.resource.assert_trigger()

    def _get_status_byte(self, iprop):
        return self.resource.read_stb()


class VisaRegisterInstrument(BaseVisaInstrument):
    """Base class for driver based on VISA and a binary registry.

    This covers among others PXI, ...

    """
    def read_memory(self, space, offset, width, extended=False):
        """See Pyvisa docs.

        """
        return self.resource.read_memory(space, offset, width, extended)

    def write_memory(self, space, offset, data, width, extended=False):
        """See Pyvisa docs.

        """
        return self.resource.write_memory(space, offset, data, width, extended)

    def move_in(self, space, offset, length, width, extended=False):
        """See Pyvisa docs.

        """
        return self.resource.move_in(space, offset, length, width, extended)

    def move_out(self, space, offset, length, data, width, extended=False):
        """See Pyvisa docs.

        """
        return self.resource.move_out(space, offset, length, data, width,
                                      extended)
