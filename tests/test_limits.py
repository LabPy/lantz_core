# -*- coding: utf-8 -*-
"""
    tests.test_limits
    ~~~~~~~~~~~~~~~~~

    Module dedicated to testing limits validators.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pytest import raises, mark

from lantz_core.limits import IntLimitsValidator, FloatLimitsValidator
from lantz_core import unit
from lantz_core.unit import get_unit_registry


def teardown_module():
    unit.UNIT_REGISTRY = None


class TestIntLimitsValidator(object):

    def test_validate_larger(self):
        iv = IntLimitsValidator(0)

        assert iv.validate(2)
        assert iv.validate(0)
        assert not iv.validate(-1)

    def test_validate_smaller(self):
        iv = IntLimitsValidator(max=1)

        assert iv.validate(0)
        assert iv.validate(1)
        assert not iv.validate(2)

    def test_validate_range(self):
        iv = IntLimitsValidator(1, 4)

        assert iv.validate(2)
        assert iv.validate(1)
        assert iv.validate(4)
        assert not iv.validate(0)
        assert not iv.validate(5)

    def test_validate_larger_and_step(self):
        iv = IntLimitsValidator(1, step=2)

        assert iv.validate(3)
        assert iv.validate(1)
        assert not iv.validate(0)
        assert not iv.validate(2)

    def test_validate_smaller_and_step(self):
        iv = IntLimitsValidator(max=5, step=2)

        assert iv.validate(3)
        assert iv.validate(5)
        assert not iv.validate(6)
        assert not iv.validate(4)

    def test_validate_range_and_step(self):
        iv = IntLimitsValidator(1, 4, 2)

        assert iv.validate(3)
        assert iv.validate(1)
        assert not iv.validate(6)
        assert not iv.validate(4)
        assert not iv.validate(0)

    def test_zero_step(self):
        iv = IntLimitsValidator(0, 5, 0)

        assert iv.validate(2)
        assert iv.validate(0)
        assert not iv.validate(-1)

    def test_init_checks(self):
        with raises(ValueError):
            IntLimitsValidator(step=1)
        with raises(TypeError):
            IntLimitsValidator(1.0)
        with raises(TypeError):
            IntLimitsValidator(max=1.0)
        with raises(TypeError):
            IntLimitsValidator(1, step=1.0)


class TestFloatLimitsValidator(object):

    def test_validate_larger(self):
        iv = FloatLimitsValidator(0)

        assert iv.validate(2.1)
        assert iv.validate(0.1)
        assert not iv.validate(-0.05)

    def test_validate_smaller(self):
        iv = FloatLimitsValidator(max=1.1)

        assert iv.validate(1.1)
        assert iv.validate(1)
        assert not iv.validate(2.3)

    def test_validate_range(self):
        iv = FloatLimitsValidator(1.5, 4.2)

        assert iv.validate(1.5)
        assert iv.validate(4.2)
        assert iv.validate(2.3)
        assert not iv.validate(1.499999)
        assert not iv.validate(4.200002)

    def test_validate_larger_and_step(self):
        iv = FloatLimitsValidator(1.0, step=0.1)

        assert iv.validate(1.0)
        assert iv.validate(1.1)
        assert iv.validate(10000000.9)
        assert not iv.validate(0.999999)
        assert not iv.validate(1.05)

    def test_validate_smaller_and_step(self):
        iv = FloatLimitsValidator(max=5.1, step=0.0001)

        assert iv.validate(5.1)
        assert iv.validate(4.0002)
        assert not iv.validate(6)
        assert not iv.validate(5.00001)

    def test_validate_range_and_step(self):
        iv = FloatLimitsValidator(1.1, 4.2, 0.02)

        assert iv.validate(1.1)
        assert iv.validate(4.2)
        assert iv.validate(1.12)
        assert not iv.validate(6)
        assert not iv.validate(4.01)
        assert not iv.validate(0)

    def test_zero_step(self):
        iv = FloatLimitsValidator(0.0, step=0.0)

        assert iv.validate(2.1)
        assert iv.validate(0.1)
        assert not iv.validate(-0.05)

    def test_init_checks(self):
        FloatLimitsValidator(1)
        with raises(ValueError):
            FloatLimitsValidator(step=1)
        with raises(TypeError):
            FloatLimitsValidator(object())
        with raises(TypeError):
            FloatLimitsValidator(max=type)
        with raises(TypeError):
            FloatLimitsValidator(1.0, step='1')

    @mark.skipif(unit.UNIT_SUPPORT is False, reason="Requires Pint")
    def test_unit_conversion(self):
        fv = FloatLimitsValidator(-1.0, 1.0, unit='V')
        u = get_unit_registry()
        assert fv.validate(0.1)
        assert fv.validate(100*u.parse_expression('mV'))
        assert not fv.validate(0.1*u.parse_expression('kV'))
