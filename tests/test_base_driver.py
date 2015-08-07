# -*- coding: utf-8 -*-
"""
    tests.test_base_driver
    ~~~~~~~~~~~~~~~~~~~~~~

    Test base driver functionalities.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pytest import raises

from lantz_core.base_driver import BaseDriver


def test_bdriver_multiple_creation():
    a = BaseDriver(a=1)
    assert hasattr(a, 'owner') is True
    assert hasattr(a, 'lock') is True
    assert a.newly_created is True
    b = BaseDriver(a=1)
    assert a is b
    assert b.newly_created is False

    class Aux(BaseDriver):
        pass

    c = Aux(a=1)
    assert c is not b


def test_bdriver_initiliaze():
    with raises(NotImplementedError):
        BaseDriver(a=1).initialize()


def test_bdriver_finalize():
    with raises(NotImplementedError):
        BaseDriver(a=1).finalize()


def test_bdriver_check():
    assert not BaseDriver(a=1).check_connection()


def test_bdriver_connected():
    with raises(NotImplementedError):
        BaseDriver(a=1).connected


def test_bdriver_context():

    class Driver(BaseDriver):

        def initialize(self):
            self._c = True

        def finalize(self):
            self._c = False

        @property
        def connected(self):
            return self._c

    with Driver() as d:
        assert d.connected
