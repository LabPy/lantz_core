# -*- coding: utf-8 -*-
"""
    tests.features.test_util.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for the tools to customize feature and help in their writings.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pytest import raises
from stringparser import Parser

from lantz_core.features.feature import Feature, get_chain, set_chain
from lantz_core.features.util import PostGetComposer
from lantz_core.errors import LantzError
from ..testing_tools import DummyParent


class TestFeatureInit(object):
    """Test that all init parameters are correctly stored.

    This class can easily be extended to other feature by overriding the
    parameters class attribute with the added keywords, and the cls attribute.

    """
    cls = Feature

    defaults = dict(getter=True, setter=True)

    parameters = dict(extract='{}',
                      retries=1,
                      checks='1>0',
                      discard={'limits': 'test'}
                      )

    exclude = list()

    def test_init(self):

        e = []
        for c in type.mro(type(self)):
            if c is not object:
                e.extend(c.exclude)
        p = {}
        d = {}
        for c in type.mro(type(self)):
            if c is not object:
                p.update(c.parameters)
                d.update(c.defaults)

        for k, v in p.items():
            if k not in e:
                kwargs = d.copy()
                kwargs[k] = v
                feat = self.cls(**kwargs)
                assert feat.creation_kwargs[k] == v


def test_standard_post_set():
    """Test the standard post_set method relying on the driver checks.

    """
    feat = Feature()
    driver = DummyParent()

    feat.post_set(driver, 1, 1.0, None)
    assert driver.d_check_instr == 1

    with raises(LantzError):
        driver.pass_check = False
        feat.post_set(driver, 1, 1.0, None)

    with raises(LantzError):
        driver.check_mess = 'Error'
        feat.post_set(driver, 1, 1.0, None)


def test_multiple_set():
    """Test multiple repeated setting of the same value.

    """
    class SetTester(DummyParent):

        feat = Feature(setter='set {}')

    driver = SetTester(True)
    driver.feat = 1
    assert driver.d_set_called == 1
    driver.feat = 1
    assert driver.d_set_called == 1


def test_del():
    """Test deleting a feature does clear the cache.

    """
    class SetTester(DummyParent):

        feat = Feature(setter='set {}')

    driver = SetTester(True)
    driver.feat = 1
    assert driver.d_set_called == 1
    del driver.feat
    driver.feat = 1
    assert driver.d_set_called == 2


def test_get_chain():
    """Test the get_chain capacity to iterate in case of driver issue.

    """
    driver = DummyParent()
    driver.retries_exceptions = (LantzError,)
    driver.d_get_raise = LantzError

    feat = Feature(True, retries=1)

    with raises(LantzError):
        get_chain(feat, driver)

    assert driver.d_get_called == 2


def test_set_chain():
    """Test the set_chain capacity to iterate in case of driver issue.
    """
    driver = DummyParent()
    driver.retries_exceptions = (LantzError,)
    driver.d_set_raise = LantzError

    feat = Feature(setter=True, retries=1)

    with raises(LantzError):
        set_chain(feat, driver, 1)

    assert driver.d_set_called == 2


def test_discard_cache():
    """Test discarding the cache associated with a feature.

    """

    class Cache(DummyParent):

        val = 1

        feat_cac = Feature(getter=True)
        feat_dis = Feature(setter=True, discard=('feat_cac',))

        def _get_feat_cac(self, feat):
            return self.val

        def _set_feat_dis(self, feature, val):
            self.val = val

    driver = Cache(True)
    assert driver.feat_cac == 1
    driver.val = 2
    assert driver.feat_cac == 1
    driver.feat_dis = 3
    assert driver.feat_cac == 3


def test_discard_cache2():
    """Test discarding the cache of both features and limits.

    """

    class Cache(DummyParent):

        val = 1
        li = 1

        feat_cac = Feature(getter=True)
        feat_dis = Feature(setter=True, discard={'features': ('feat_cac',),
                                                 'limits': ('lim', )})

        def _get_feat_cac(self, feat):
            return self.val

        def _set_feat_dis(self, feature, val):
            self.val = val

        def _limits_lim(self):
            self.li += 1
            return self.li

    driver = Cache(True)
    assert driver.feat_cac == 1
    assert driver.get_limits('lim') == 2
    driver.val = 2
    assert driver.feat_cac == 1
    assert driver.get_limits('lim') == 2
    driver.feat_dis = 3
    assert driver.feat_cac == 3
    assert driver.get_limits('lim') == 3


def test_discard_cache3():
    """Test discarding the cache of limits only.

    """

    class Cache(DummyParent):

        val = 1
        li = 1

        feat_dis = Feature(setter=True, discard={'limits': ('lim', )})

        def _set_feat_dis(self, feature, val):
            self.val = val

        def _limits_lim(self):
            self.li += 1
            return self.li

    driver = Cache(True)
    assert driver.get_limits('lim') == 2
    driver.val = 2
    assert driver.get_limits('lim') == 2
    driver.feat_dis = 3
    assert driver.get_limits('lim') == 3


def test_feature_checkers():
    """Test use of checks keyword in Feature.

    """

    class AuxParent(DummyParent):

        aux = 1
        feat = Feature(True)
        feat_ch = Feature(True, True,
                          checks='driver.aux==1; driver.feat is True')
        feat_gch = Feature(True, True, checks=('driver.aux==1', None))
        feat_sch = Feature(True, True, checks=(None, 'driver.aux==1'))

    assert hasattr(AuxParent.feat_ch, 'get_check')
    assert hasattr(AuxParent.feat_ch, 'set_check')
    assert hasattr(AuxParent.feat_gch, 'get_check')
    assert not hasattr(AuxParent.feat_gch, 'set_check')
    assert not hasattr(AuxParent.feat_sch, 'get_check')
    assert hasattr(AuxParent.feat_sch, 'set_check')

    driver = AuxParent()
    driver.feat_ch
    driver.feat_gch
    driver.feat_sch
    driver.feat_ch = 1
    driver.feat_gch = 1
    driver.feat_sch = 1

    driver.aux = False
    with raises(AssertionError):
        driver.feat_ch
    with raises(AssertionError):
        driver.feat_gch
    driver.feat_sch
    with raises(AssertionError):
        driver.feat_ch = 1
    driver.feat_gch = 1
    with raises(AssertionError):
        driver.feat_sch = 1


def test_clone():
    """Test cloning a feature.

    """

    feat_ch = Feature(True, True, checks='driver.aux==1; driver.feat is True')
    new = feat_ch.clone()
    assert feat_ch.pre_get is not new.pre_get
    assert feat_ch._customs is not new._customs


def test_modify_behavior1():
    """Modify by replacing by a stand-alone method

    """

    feat = Feature()
    meth = lambda d, f, v: v
    feat.modify_behavior('post_get', meth)
    assert feat.post_get.__func__._feat_wrapped_ is meth
    assert feat._customs['post_get'].__func__._feat_wrapped_ is meth


def test_modify_behavior2():
    """Modify a method that has not yet a MethodsComposer.

    """

    feat = Feature()
    meth = lambda d, v: v
    feat.modify_behavior('post_get', meth, ('custom', 'append',))
    assert isinstance(feat.post_get, PostGetComposer)
    assert 'custom' in feat._customs['post_get']
    assert feat._customs['post_get']['custom'][1:] == ('append',)
    assert (feat._customs['post_get']['custom'][0].__func__._feat_wrapped_ ==
            meth)


def test_modify_behavior():
    """Test all possible cases of behaviour modifications.

    """
    test = Feature(True, True)

    # Test replacing a method.
    test.modify_behavior('get', lambda s, d: 1)
    assert test.get(None) == 1

    def r(s, d):
        raise ValueError()

    test.modify_behavior('pre_get', r)
    with raises(ValueError):
        test.pre_get(None)

    # Test modifying and already customized method.
    def r2(s, d):
        raise KeyError()

    test.modify_behavior('pre_get', r2, ('custom', 'prepend'))
    with raises(KeyError):
        test.pre_get(None)

    test.modify_behavior('pre_get', None, ('custom', 'remove'))
    with raises(ValueError):
        test.pre_get(None)

    test.modify_behavior('pre_get', r2, ('custom', 'add_before', 'old'))
    with raises(KeyError):
        test.pre_get(None)

    test.modify_behavior('pre_get', lambda s, d: 1, ('custom', 'replace'))
    with raises(ValueError):
        test.pre_get(None)

    # Test replacing and internal customization.
    def r(s, d, v):
        raise ValueError()

    def r2(s, d, v):
        raise KeyError()

    test.modify_behavior('post_get', r, ('test1', 'prepend'), True)
    test.modify_behavior('post_get', r2, ('test2', 'append'), True)

    test.modify_behavior('post_get', lambda s, d, v: 1, ('test1', 'replace'))
    with raises(KeyError):
        test.post_get(None, 0)

    test.modify_behavior('post_get', r, ('test2', 'replace'))
    with raises(ValueError):
        test.post_get(None, 0)


def test_copy_custom_behaviors():
    """Test copy customs behaviors.

    """
    def r2(s, d, v):
        raise KeyError()

    modified_feature = Feature(True, True, checks='1 < 2', extract='{}')
    modified_feature.modify_behavior('get', lambda s, d: 1)
    modified_feature.modify_behavior('pre_get', lambda s, d: 1,
                                     ('custom', 'add_before', 'checks'))
    modified_feature.modify_behavior('post_get', lambda s, d, v: 2*v,
                                     ('custom', 'add_after', 'extract'))
    modified_feature.modify_behavior('pre_set', lambda s, d, v: 1,
                                     ('aux', 'prepend'))
    modified_feature.modify_behavior('pre_set', lambda s, d, v: 1,
                                     ('aux2', 'append'))
    modified_feature.modify_behavior('pre_set', r2,
                                     ('custom', 'add_after', 'checks'))
    modified_feature.modify_behavior('post_set', lambda s, d, v: 1,
                                     ('aux', 'prepend'), True)
    modified_feature.modify_behavior('post_set', lambda s, d, v: 1,
                                     ('custom', 'add_after', 'aux'))

    feat = Feature(True, True, extract='{}')
    feat.modify_behavior('pre_set', lambda s, d, v: 1, ('test', 'append'))
    feat.modify_behavior('pre_get', lambda s, d: 1, ('test', 'append'))
    feat.copy_custom_behaviors(modified_feature)

    assert feat.get(None) == 1
    with raises(KeyError):
        feat.pre_set(None, 1)

def test_extract():
    """Test extracting a value, when extract is a string.

    """

    feat = Feature(extract='The value is {:d}')
    val = feat.post_get(None, 'The value is 11')
    assert val == 11

    feat = Feature(extract=Parser('The value is {:d}'))
    val = feat.post_get(None, 'The value is 11')
    assert val == 11

# Other behaviors are tested by the tests in test_has_features.py
