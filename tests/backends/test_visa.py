# -*- coding: utf-8 -*-
"""
    tests.backends.test_visa.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Test VISA backend.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import os

import pytest

pytest.importorskip('lantz_core.backends.visa')
pytest.importorskip('pyvisa-sim')

from pyvisa.highlevel import ResourceManager
from lantz_core.features import Float
from lantz_core.errors import InterfaceNotSupported
from lantz_core.backends.visa import (get_visa_resource_manager,
                                      set_visa_resource_manager,
                                      BaseVisaDriver,
                                      VisaMessageDriver,
                                      VisaRegisterDriver,
                                      errors,
                                      to_canonical_name)

base_backend = os.path.join(os.path.dirname(__file__), 'base.yaml@sim')


# --- Test resource managers handling -----------------------------------------

@pytest.yield_fixture
def cleanup():
    yield
    import lantz_core.backends.visa as lv
    lv._RESOURCE_MANAGERS = None


def test_get_visa_resource_manager(cleanup):

    rm = get_visa_resource_manager('@py')
    assert rm is get_visa_resource_manager('@py')

    assert rm is not get_visa_resource_manager('@sim')
    import lantz_core.backends.visa as lv
    assert len(lv._RESOURCE_MANAGERS) == 2


def test_set_visa_resource_manager(cleanup):

    rm = ResourceManager('@py')
    set_visa_resource_manager(rm, '@py')
    assert rm is get_visa_resource_manager('@py')

    with pytest.raises(ValueError):
        set_visa_resource_manager(rm, '@py')

    rm = ResourceManager('@sim')
    set_visa_resource_manager(rm, '@sim')
    assert rm is get_visa_resource_manager('@sim')


# --- Test base driver capabilities -------------------------------------------

@pytest.fixture
def visa_driver():
    """Fixture returning a basic visa driver.

    """
    return BaseVisaDriver({'interface_type': 'TCPIP',
                           'host_address': '192.168.0.100',
                           'backend': base_backend})


class TestBaseVisaDriver(object):

    def test_visa_driver_unicity(self, visa_driver):
        """Test that visa name normalization ensure driver unicity.

        """
        rname = 'TCPIP::192.168.0.100::INSTR'
        driver2 = BaseVisaDriver({'resource_name': rname,
                                  'backend': base_backend})
        assert visa_driver.resource_name == driver2.resource_name
        assert visa_driver is driver2

    def test_handling_a_visa_alias(self):
        """Check that a visa alias can be accepted.

        """
        rname = 'visa_alias'
        driver = BaseVisaDriver({'resource_name': rname,
                                 'backend': base_backend})
        assert driver.resource_name == 'visa_alias'

    def test_filling_infos_from_PROTOCOLS(self):
        """Test that infos provided in the PROTOCOLS class attribute are correctly
        picked

        """
        class TestVisaDriver(BaseVisaDriver):

            PROTOCOLS = {'TCPIP': {'resource_class': 'SOCKET',
                                   'port': 5025}}

        driver = TestVisaDriver({'interface_type': 'TCPIP',
                                 'host_address': '192.168.0.100',
                                 'backend': base_backend})

        rname = 'TCPIP::192.168.0.100::5025::SOCKET'
        driver2 = TestVisaDriver({'resource_name': rname,
                                  'backend': base_backend})

        assert driver.resource_name == driver2.resource_name
        assert driver is driver2

        TestVisaDriver.PROTOCOLS = {'TCPIP': [{'resource_class': 'INSTR',
                                               'lan_device_name': 'inst1'},
                                              {'resource_class': 'SOCKET',
                                               'port': 5025}]}

        driver = TestVisaDriver({'interface_type': 'TCPIP',
                                 'host_address': '192.168.0.100',
                                 'backend': base_backend})

        rname = 'TCPIP::192.168.0.100::inst1::INSTR'
        driver2 = TestVisaDriver({'resource_name': rname,
                                  'backend': base_backend})

        assert driver.resource_name == driver2.resource_name
        assert driver is driver2

    def test_using_default_and_para(self):
        """Test mixing default parameters and user custom ones.

        """
        class TestDefaultVisa(VisaMessageDriver):

            DEFAULTS = {'TCPIP': {'read_termination': '\n'},
                        'COMMON': {'write_termination': '\n',
                                   'timeout': 10}}

        driver = TestDefaultVisa({'interface_type': 'TCPIP',
                                  'host_address': '192.168.0.1',
                                  'backend': base_backend,
                                  'para': {'timeout': 5}})

        assert driver.resource_kwargs == {'read_termination': '\n',
                                          'write_termination': '\n',
                                          'timeout': 5}

    def test_using_forbidden_interface(self):
        """Test creating an instance for a forbidden interface type.

        """
        class TestDefaultVisa(VisaMessageDriver):

            DEFAULTS = {'TCPIP': None,
                        'COMMON': {'write_termination': '\n',
                                   'timeout': 10}}

        with pytest.raises(InterfaceNotSupported):
            TestDefaultVisa({'interface_type': 'TCPIP',
                             'host_address': '192.168.0.1',
                             'backend': base_backend,
                             'para': {'timeout': 5}})

    def test_clear(self, visa_driver):
        """Test clearing an instrument.

        """
        visa_driver.initialize()
        with pytest.raises(NotImplementedError):
            visa_driver.clear()

    def test_resource_info(self, visa_driver):
        """Test querying the underlying resource infos.

        """
        visa_driver.initialize()
        assert visa_driver.resource_info

    def test_interface_type(self, visa_driver):
        """Test querying the underlying resource interface type.

        """
        visa_driver.initialize()
        assert visa_driver.interface_type

    def test_timeout(self, visa_driver):
        """Test the timeout descriptor.

        """
        assert visa_driver.timeout is None
        visa_driver.timeout = 10
        visa_driver.initialize()
        assert visa_driver.timeout == 10
        del visa_driver.timeout
        assert visa_driver.timeout == float('+inf')

    def test_reopen_connection(self, visa_driver, monkeypatch):
        """Test reopening a connections.

        """
        class Witness(object):

            def __init__(self):
                self.called = 0

            def __call__(self):
                self.called += 1

        visa_driver.initialize()
        visa_driver.timeout = 20
        w = Witness()
        monkeypatch.setattr(type(visa_driver._resource), 'clear',  w)

        visa_driver.reopen_connection()
        assert visa_driver._resource
        assert w.called == 1
        assert visa_driver.timeout == 20

    def test_install_handler(self, visa_driver):
        """Test clearing an instrument.

        """
        visa_driver.initialize()
        with pytest.raises(NotImplementedError):
            visa_driver.install_handler(None, None)

    def test_uninstall_handler(self, visa_driver):
        """Test clearing an instrument.

        """
        visa_driver.initialize()
        with pytest.raises(errors.UnknownHandler):
            visa_driver.uninstall_handler(None, None)


# --- Test message driver specific methods ------------------------------------

class TestVisaMessage(VisaMessageDriver):

    MANUFACTURER_ID = '0xB21'

    MODEL_CODE = '0x39'


class TestVisaMessageDriver(object):

# TODO need support for query in list_resources for @sim backend
#    def test_via_usb_instr(self):
#
#        driver = TestVisaMessage.via_usb('90N326143',
#                                          backend=base_backend)
#        assert driver.resource_name ==\
#            to_canonical_name('USB::0xB21::0x39::90N326143::INSTR')
#        driver.initialize()

#    def test_via_usb_raw(self):
#
#        driver = TestVisaMessage.via_usb_raw('90N326143',
#                                             backend=base_backend)
#        assert driver.resource_name ==\
#            to_canonical_name('USB::0xB21::0x39::90N326143::RAW')
#        driver.initialize()

    def test_via_tcpip_instr(self):

        driver = TestVisaMessage.via_tcpip('192.168.0.100',
                                           backend=base_backend)
        assert driver.resource_name ==\
            to_canonical_name('TCPIP::192.168.0.100::inst0::INSTR')
        driver.initialize()

    def test_via_tcpip_socket(self):

        driver = TestVisaMessage.via_tcpip_socket('192.168.0.100', 5025,
                                                  backend=base_backend)
        assert driver.resource_name ==\
            to_canonical_name('TCPIP::192.168.0.100::5025::SOCKET')
        driver.initialize()

    def test_via_serial(self):

        driver = TestVisaMessage.via_serial(1, backend=base_backend)
        assert driver.resource_name == to_canonical_name('ASRL1::INSTR')
        driver.initialize()

    def test_via_gpib(self):

        driver = TestVisaMessage.via_gpib(1, backend=base_backend)
        assert driver.resource_name == to_canonical_name('GPIB::1::INSTR')
        driver.initialize()

    def test_feature(self):
        """Test getting and setting a feature.

        """
        class TestFeature(VisaMessageDriver):

            freq = Float('?FREQ', 'FREQ {}')

            DEFAULTS = {'COMMON': {'write_termination': '\n',
                                   'read_termination': '\n'}}

            def default_check_operation(self, feat, value, i_value,
                                        state=None):
                return True, ''

        d = TestFeature.via_tcpip('192.168.0.100', backend=base_backend)
        d.initialize()
        assert d.freq == 100.0
        d.freq = 10.
        assert d.freq == 10.

    def test_status_byte(self):
        pass

    def test_write_raw(self):

        with pytest.raises(NotImplementedError):
            self.driver.write_raw('')

    def test_write(self):
        with pytest.raises(NotImplementedError):
            self.driver.write('')

    def test_write_ascii_values(self):

        with pytest.raises(NotImplementedError):
            self.driver.write_ascii_values('VAL', range(10), 'f', ',')

    def test_write_binary_values(self):

        pass

    def test_read_raw(self, size=None):

        pass

    def test_read(self):

        pass

    def test_read_values(self):

        pass

    def test_query(self):

        pass

    def test_query_ascii_values(self):

        pass

    def test_query_binary_values(self):

        pass


class TestVisaRegistryDriver(object):
    """Test the VisaRegistryDriver capabilities.

    Use an abstract visa library as we don't have a simulated backend yet.

    """
    def test_move_in(self):

        pass

    def test_move_out(self):

        pass

    def test_read_memory(self):

        pass

    def test_write_memory(self):

        pass
