# -*- coding: utf-8 -*-
"""
    tests.test_unit
    ~~~~~~~~~~~~~~~

    Module dedicated to testing the unit utility functions.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pytest import raises, yield_fixture, mark

from lantz_core import unit
from lantz_core.unit import set_unit_registry, get_unit_registry

try:
    from pint import UnitRegistry
except ImportError:
    pass


@yield_fixture
def teardown():
    unit.UNIT_REGISTRY = None
    yield
    unit.UNIT_REGISTRY = None


@mark.skipif(unit.UNIT_SUPPORT is False, reason="Requires Pint")
def test_set_unit_registry(teardown):
    ureg = UnitRegistry()
    set_unit_registry(ureg)

    assert get_unit_registry() is ureg


@mark.skipif(unit.UNIT_SUPPORT is False, reason="Requires Pint")
def test_reset_unit_registry(teardown):
    ureg = UnitRegistry()
    set_unit_registry(ureg)
    with raises(ValueError):
        set_unit_registry(ureg)
