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

from lantz_core.backends.visa import (get_visa_resource_manager,
                                      set_visa_resource_manager,
                                      assemble_resource_name,
                                      BaseVisaDriver,
                                      VisaMessageDriver)


def test_get_visa_resource_manager():
    pass


def test_set_visa_resource_manager():
    pass


def test_assemble_resource_name():
    pass


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
