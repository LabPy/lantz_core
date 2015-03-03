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

from lantz_core.features.feature import Feature
from lantz_core.features.util import PostGetComposer
from ..testing_tools import DummyParent


def test_discard_cache():

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


def test_feature_checkers():

    class AuxParent(DummyParent):

        aux = 1
        feat = Feature(True)
        feat_ch = Feature(True, True, checks='{aux}==1; {feat} is True')
        feat_gch = Feature(True, True, checks=('{aux}==1', None))
        feat_sch = Feature(True, True, checks=(None, '{aux}==1'))

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

    feat_ch = Feature(True, True, checks='{aux}==1; {feat} is True')
    new = feat_ch.clone()
    assert feat_ch.pre_get is not new.pre_get
    assert feat_ch._customs is not new._customs


# Modify by replacing by a stand-alone method
def test_modify_behavior1():

    feat = Feature()
    meth = lambda d, f, v: v
    feat.modify_behavior('post_get', meth)
    assert feat.post_get.__func__._feat_wrapped_ is meth
    assert feat._customs['post_get'].__func__._feat_wrapped_ is meth


# Modify a method that has not yet a MethodsComposer.
def test_modify_behavior2():

    feat = Feature()
    meth = lambda d, v: v
    feat.modify_behavior('post_get', meth, ('custom', 'append',))
    assert isinstance(feat.post_get, PostGetComposer)
    assert 'custom' in feat._customs['post_get']
    assert feat._customs['post_get']['custom'][1:] == ('append',)
    assert (feat._customs['post_get']['custom'][0].__func__._feat_wrapped_ ==
            meth)

# Other behaviors are tested by the tests in test_has_features.py


def test_extract():
    pass
