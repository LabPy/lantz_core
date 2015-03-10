# -*- coding: utf-8 -*-
"""
    tests.features.test_scalars
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Module dedicated to testing the scalars features.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pytest import raises, mark

from lantz_core.features.scalars import Unicode, Int, Float
from lantz_core.limits import IntLimitsValidator, FloatLimitsValidator
from lantz_core.unit import get_unit_registry, UNIT_SUPPORT
from ..testing_tools import DummyParent


def test_unicode():
    u = Unicode(setter=True, values=['On', 'Off'])
    assert u.pre_set(None, 'On') == 'On'
    with raises(ValueError):
        u.pre_set(None, 'TEST')
    assert isinstance(u.post_get(None, 1), type(''))


class TestInt(object):

    def test_post_get(self):
        i = Int()
        assert i.post_get(None, '11') == 11

    def test_with_values(self):
        i = Int(setter=True, values=(1, 2, 3))
        assert i.pre_set(None, 2) == 2
        with raises(ValueError):
            i.pre_set(None, 5)
        del i.pre_set
        assert i.pre_set(None, 5)

    def test_with_static_limits(self):
        i = Int(setter=True, values=(1,), limits=IntLimitsValidator(2, step=2))
        with raises(ValueError):
            i.pre_set(None, 1)
        assert i.pre_set(None, 4)
        with raises(ValueError):
            i.pre_set(None, 3)

    def test_with_dynamic_limits(self):

        class LimitsHolder(DummyParent):

            n = 0

            def _limits_test(self):
                self.n += 1
                return IntLimitsValidator(self.n)
        o = LimitsHolder()
        i = Int(setter=True, limits='test')
        assert i.pre_set(o, 1)
        with raises(ValueError):
            i.pre_set(o, 0)
        o.discard_limits(('test', ))
        with raises(ValueError):
            i.pre_set(o, 1)


class TestFloat(object):

    def test_post_get(self):
        f = Float()
        assert f.post_get(None, '0.1') == 0.1

    @mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
    def test_post_get_with_unit(self):
        f = Float(unit='V')
        assert hasattr(f.post_get(None, 0.1), 'magnitude')
        assert f.post_get(None, 0.1).to('mV').magnitude == 100.

    def test_with_values(self):
        f = Float(setter=True, values=(1.0, 2.4, 3.1))
        assert f.pre_set(None, 2.4) == 2.4
        with raises(ValueError):
            f.pre_set(None, 5)
        del f.pre_set
        assert f.pre_set(None, 5)

    @mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
    def test_with_values_and_units(self):
        f = Float(setter=True, values=(1.0, 2.4, 3.1), unit='mV')
        u = get_unit_registry()
        assert f.pre_set(None, 1.0) == 1.0
        assert f.pre_set(None, u.parse_expression('0.0024 V')) == 2.4

    def test_set_with_static_limits(self):
        f = Float(setter=True, limits=FloatLimitsValidator(0.0))
        assert f.pre_set(None, 0.1) == 0.1
        with raises(ValueError):
            f.pre_set(None, -1.0)

    def test_set_with_dynamic_limits(self):

        class LimitsHolder(DummyParent):

            n = 0.1

            def _limits_test(self):
                self.n += .1
                return FloatLimitsValidator(0.0, step=self.n)

        o = LimitsHolder()
        f = Float(setter=True, limits='test')
        assert f.pre_set(o, .2)
        with raises(ValueError):
            f.pre_set(o, -0.5)
        o.discard_limits(('test', ))
        with raises(ValueError):
            f.pre_set(o, 0.2)

    @mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
    def test_set_with_unit(self):
        f = Float(setter=True, unit='mV')
        u = get_unit_registry()
        assert f.pre_set(None, u.parse_expression('10 V')) == 10000.

    @mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
    def test_with_static_limits_and_units(self):
        f = Float(setter=True,
                  limits=FloatLimitsValidator(-1.0, 1.0, 0.01, unit='V'))
        u = get_unit_registry()
        assert f.pre_set(None, 0.1) == 0.1
        with raises(ValueError):
            f.pre_set(None, -2.0)
        assert f.pre_set(None, u.parse_expression('10 mV')) == 10.
        with raises(ValueError):
            f.pre_set(None, u.parse_expression('0.1 mV'))

    @mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
    def test_with_dynamic_limits_and_units(self):

        class LimitsHolder(DummyParent):

            n = 0.0

            def _limits_test(self):
                self.n += 100
                return FloatLimitsValidator(-1000., 1000., step=self.n,
                                            unit='mV')

        o = LimitsHolder()
        f = Float(setter=True, limits='test', unit='V')
        assert f.pre_set(o, .1) == 0.1
        with raises(ValueError):
            f.pre_set(o, -5)
        o.discard_limits(('test', ))
        with raises(ValueError):
            f.pre_set(o, 0.1)

        u = get_unit_registry()
        assert f.pre_set(o, u.parse_expression('200 mV')) == 0.2
        with raises(ValueError):
            f.pre_set(o, u.parse_expression('100 mV'))
