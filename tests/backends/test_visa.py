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

from pyvisa.highlevel import ResourceManager
from pytest import yield_fixture, raises
from lantz_core.backends.visa import (get_visa_resource_manager,
                                      set_visa_resource_manager,
                                      assemble_resource_name,
                                      BaseVisaDriver,
                                      VisaMessageDriver)


@yield_fixture
def cleanup():
    yield
    import lantz_core.backends.visa as lv
    lv._RESOURCE_MANAGER = None


def test_get_visa_resource_manager(cleanup):

    rm = get_visa_resource_manager('@py')
    assert rm is get_visa_resource_manager('@py')

    assert rm is not get_visa_resource_manager('@sim')
    import lantz_core.backends.visa as lv
    assert len(lv._RESOURCE_MANAGER) == 2


def test_set_visa_resource_manager(cleanup):

    rm = ResourceManager('@py')
    set_visa_resource_manager(rm, '@py')
    assert rm is get_visa_resource_manager('@py')

    with raises(ValueError):
        set_visa_resource_manager(rm, '@py')

    rm = ResourceManager('@sim')
    set_visa_resource_manager(rm, '@sim')
    assert rm is get_visa_resource_manager('@sim')


class TestAssembleResourceName():

    def test_serial(self):
        r_dict = {'type': 'ASRL', 'address': 1}
        assert 'ASRL1::INSTR' == assemble_resource_name(r_dict)

    def test_gpib(self):
        r_dict = {'type': 'GPIB', 'address': 1}
        assert 'GPIB0::1::INSTR' == assemble_resource_name(r_dict)

    def test_gpib_with_board(self):
        r_dict = {'type': 'GPIB', 'address': 1, 'board': 2}
        assert 'GPIB2::1::INSTR' == assemble_resource_name(r_dict)

    def test_pxi(self):
        r_dict = {'type': 'PXI', 'address': 1}
        assert 'PXI0::1::INSTR' == assemble_resource_name(r_dict)

    def test_pxi_with_board(self):
        r_dict = {'type': 'PXI', 'address': 1, 'board': 2}
        assert 'PXI2::1::INSTR' == assemble_resource_name(r_dict)

    def test_usb_instr(self):
        r_dict = {'type': 'USB', 'address': '0x11::0x21:125687'}
        assert 'USB0::0x11::0x21:125687::INSTR' ==\
            assemble_resource_name(r_dict)

    def test_usb_raw_with_board(self):
        r_dict = {'type': 'USB', 'address': '0x11::0x21:125687', 'board': 1,
                  'mode': 'RAW'}
        assert 'USB1::0x11::0x21:125687::RAW' ==\
            assemble_resource_name(r_dict)

    def test_tcpip_instr(self):
        r_dict = {'type': 'TCPIP', 'address': '192.168.0.2', 'board': 2}
        assert 'TCPIP2::192.168.0.2::inst0::INSTR' ==\
            assemble_resource_name(r_dict)

    def test_tcpip_socket_with_board_and_hostname(self):
        r_dict = {'type': 'TCPIP', 'address': '192.168.0.2',
                  'hostname': 'test', 'mode': 'SOCKET', 'port': 5000}
        assert 'TCPIP0::192.168.0.2::test::5000::SOCKET' ==\
            assemble_resource_name(r_dict)

    def test_missing_port(self):
        r_dict = {'type': 'TCPIP', 'address': '192.168.0.2',
                  'hostname': 'test', 'mode': 'SOCKET'}
        with raises(ValueError):
            assemble_resource_name(r_dict)

    def test_unsupported_mode(self):
        r_dict = {'type': 'TCPIP', 'address': '192.168.0.2',
                  'hostname': 'test', 'mode': 'TEST'}
        with raises(ValueError):
            assemble_resource_name(r_dict)


class TestBaseVisaDriver(object):
    """
    """
    def setup(self):
        pass

    def test_driver_unicity(self):
        pass

    def test_resource_info(self):
        pass

    def test_interface_type(self):
        pass

    def test_clear(self):
        pass

    def test_timeout(self):
        pass

    def test_reopen_connection(self):
        pass


class TestVisaMessageDriver(object):

    def setup(self):
        pass

    def test_via_usb_instr(self):
        pass

    def test_via_usb_raw(self):
        pass

    def test_via_tcpip_instr(self):
        pass

    def test_via_tcpip_socket(self):
        pass

    def test_encoding(self):
        pass

    def test_write_termination(self):
        pass

    def test_read_termination(self):
        pass

    def test_write(self):
        pass

    def test_read(self):
        pass

    def test_query(self):
        pass

    def test_status_byte(self):
        pass
