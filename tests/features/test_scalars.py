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

from lantz_core.features.enumerable import Enumerable
from lantz_core.features.scalars import Unicode, Int, Float
from lantz_core.limits import IntLimitsValidator, FloatLimitsValidator
from lantz_core.unit import get_unit_registry, UNIT_SUPPORT
from lantz_core.has_features import set_feat

from ..testing_tools import DummyParent
from .test_mappings import TestMappingInit
from .test_feature import TestFeatureInit
from .test_limits_validated import TestLimitsValidatedInit


class TestEnumerableInit(TestFeatureInit):

    cls = Enumerable

    parameters = dict(values=(11, 2))


class TestUnicodeInit(TestEnumerableInit, TestMappingInit):

    cls = Unicode


def test_unicode():
    u = Unicode(setter=True, values=['On', 'Off'])
    assert u.pre_set(None, 'On') == 'On'
    with raises(ValueError):
        u.pre_set(None, 'TEST')
    assert isinstance(u.post_get(None, 1), type(''))


def test_unicode_mapping():
    m = Unicode(mapping={'On': 1, 'Off': 2})
    assert m.post_get(None, 1) == 'On'
    assert m.post_get(None, 2) == 'Off'

    assert m.pre_set(None, 'On') == 1
    assert m.pre_set(None, 'Off') == 2


class TestIntInit(TestLimitsValidatedInit, TestEnumerableInit,
                  TestMappingInit):

    cls = Int


class TestInt(object):

    def test_post_get(self):
        i = Int()
        assert i.post_get(None, '11') == 11

    def test_post_get_with_extract(self):
        i = Int(extract='This is the value {}')
        assert i.post_get(None, 'This is the value 11') == 11

    def test_with_values(self):
        i = Int(setter=True, values=(1, 2, 3))
        assert i.pre_set(None, 2) == 2
        with raises(ValueError):
            i.pre_set(None, 5)
        del i.pre_set
        assert i.pre_set(None, 5)

    def test_with_mapping(self):
        m = Int(mapping={1: 'On', 2: 'Off'})
        assert m.post_get(None, 'On') == 1
        assert m.post_get(None, 'Off') == 2

        assert m.pre_set(None, 1) == 'On'
        assert m.pre_set(None, 2) == 'Off'

    def test_with_static_limits(self):
        i = Int(setter=True, values=(1,), limits=(2, 5, 2))
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


class CacheFloatTester(DummyParent):
    """Dummy object used as a base class for testing Float cache handling.

    """
    val = 1.

    fl = Float(True, True)

    def __init__(self, caching_allowed=True):
        super(CacheFloatTester, self).__init__(caching_allowed)

    def _get_fl(self, feat):
        return self.val

    def _set_fl(self, feature, val):
        self.val = val


class UnitCacheFloatTester(CacheFloatTester):
    """Same as above but with a unit.

    """
    fl = set_feat(unit='V')


class TestFloatInit(TestIntInit):

    cls = Float

    parameters = dict(unit='V')


class TestFloat(object):

    def test_post_get(self):
        f = Float()
        assert f.post_get(None, '0.1') == 0.1

    def test_post_with_extract(self):
        f = Float(extract='This is the value {}')
        assert f.post_get(None, 'This is the value 1.1') == 1.1

    @mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
    def test_post_get_with_unit(self):
        f = Float(unit='V')
        assert hasattr(f.post_get(None, 0.1), 'magnitude')
        assert f.post_get(None, 0.1).to('mV').magnitude == 100.

    @mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
    def test_post_get_with_extract_and_unit(self):
        f = Float(unit='V', extract='This is the value {}')
        val = f.post_get(None, 'This is the value 0.1')
        assert hasattr(val, 'magnitude')
        assert val.to('mV').magnitude == 100.

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

    def test_with_mapping_no_units(self):
        m = Float(mapping={1.0: 'On', 2.0: 'Off'})
        assert m.post_get(None, 'On') == 1.0
        assert m.post_get(None, 'Off') == 2.0

        assert m.pre_set(None, 1.0) == 'On'
        assert m.pre_set(None, 2.0) == 'Off'

    @mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
    def test_with_mapping_units(self):
        m = Float(mapping={1.0: 'On', 2.0: 'Off'}, unit='mV')
        u = get_unit_registry()
        assert m.post_get(None, 'On') == u.parse_expression('1.0 mV')
        assert m.post_get(None, 'Off') == u.parse_expression('2.0 mV')

        assert m.pre_set(None, u.parse_expression('0.001 V')) == 'On'
        assert m.pre_set(None, u.parse_expression('0.002 V')) == 'Off'

    def test_set_with_static_limits(self):
        f = Float(setter=True, limits=(0.0, ))
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

    def test_cache_no_unit(self):
        """Test getting a cached value when no unit is specified.

        """
        parent = CacheFloatTester()
        aux = parent.fl
        old_val = parent.val
        parent.val += 1
        assert parent.fl == aux

        parent.fl = aux
        assert parent.val != old_val

    @mark.skipif(UNIT_SUPPORT is True, reason="Requires Pint absence")
    def test_cache_unit_without_support(self):
        """Test getting a cached value with a unit in the absence of unit
        support.

        """
        parent = UnitCacheFloatTester()
        aux = parent.fl
        old_val = parent.val
        parent.val += 1
        assert parent.fl == aux
        assert not hasattr(aux, 'magnitude')

        parent.fl = aux
        assert parent.val != old_val

        parent.fl = 0.5
        assert parent.val == 0.5

    @mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
    def test_cache_get_unit_with_support(self):
        """Test getting a cached value with a unit in the presence of unit
        support.

        """
        parent = UnitCacheFloatTester()
        ureg = get_unit_registry()
        parent.val = 0.2
        assert parent.val == 0.2
        assert parent.fl == ureg.parse_expression('0.2 V')
        parent.fl = 0.1
        assert parent.fl == ureg.parse_expression('0.1 V')

        parent.val = 1
        parent.fl = ureg.parse_expression('0.1 V')
        assert parent.val == 1

        q = ureg.parse_expression('0.2 V')
        parent.fl = q
        assert parent.val == 0.2
        assert parent.fl == q

        parent.val = 1
        parent.fl = 0.2
        assert parent.val == 1
