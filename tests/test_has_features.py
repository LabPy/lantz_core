# -*- coding: utf-8 -*-
"""
    tests.test_has_features
    ~~~~~~~~~~~~~~~~~~~~~~~

    Test basic metaclasses functionalities.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pytest import raises

from lantz_core.has_features import subsystem, set_feat, channel, HasFeatures
from lantz_core.subsystem import SubSystem
from lantz_core.channel import Channel
from lantz_core.features.feature import Feature
from lantz_core.features.util import (append, prepend, add_after, add_before,
                                      replace)

from .testing_tools import DummyParent


def test_documenting_feature():

    class DocTester(DummyParent):

        #: This is the docstring for
        #: the Feature test.
        test = Feature()

    assert DocTester.test.__doc__ ==\
        'This is the docstring for the Feature test.'

# --- Test overriding features behaviors --------------------------------------


def test_customizing():

    class DecorateIP(Feature):

        def __init__(self, getter=True, setter=True, retries=0,
                     get_format=None, checks=None, discard=None, dec='<br>'):
            super(DecorateIP, self).__init__(getter, setter)
            self.dec = dec

        def post_get(self, iprop, val):
            return self.dec+val+self.dec

    class ParentTester(DummyParent):
        test = DecorateIP(getter=True, setter=True)

        def _get_test(self, iprop):
            return 'this is a test'

    class CustomizationTester(ParentTester):

        test = set_feat(dec='<it>')

    assert CustomizationTester.test is not ParentTester.test
    aux1 = ParentTester()
    aux2 = CustomizationTester()
    assert aux1.test != aux2.test
    assert aux2.test.startswith('<it>')


def test_overriding_get():

    class NoOverrideGet(DummyParent):
        test = Feature(getter=True)

    assert NoOverrideGet().test

    class OverrideGet(DummyParent):
        test = Feature(getter=True)

        def _get_test(self, iprop):
            return 'This is a test'

    assert OverrideGet().test == 'This is a test'


def test_overriding_pre_get():

    class OverridePreGet(DummyParent):
        test = Feature(getter=True)

        def _get_test(self, iprop):
            return 'this is a test'

        def _pre_get_test(self, iprop):
            assert False

    with raises(AssertionError):
        OverridePreGet().test


def test_overriding_post_get():

    class OverridePostGet(DummyParent):
        test = Feature(getter=True)

        def _get_test(self, iprop):
            return 'this is a test'

        def _post_get_test(self, iprop, val):
            return '<br>'+val+'<br>'

    assert OverridePostGet().test == '<br>this is a test<br>'


def test_overriding_set():

    class NoOverrideSet(DummyParent):
        test = Feature(setter=True)

    NoOverrideSet().test = 1

    class OverrideSet(DummyParent):
        test = Feature(setter=True)

        def _set_test(self, iprop, value):
            self.val = value

    o = OverrideSet()
    o.test = 1
    assert o.val == 1


def test_overriding_pre_set():

    class OverridePreSet(DummyParent):
        test = Feature(setter=True)

        def _set_test(self, iprop, value):
            self.val = value

        def _pre_set_test(self, iprop, value):
            return value/2

    o = OverridePreSet()
    o.test = 1
    assert o.val == 0.5


def test_overriding_post_set():

    class OverridePreSet(DummyParent):
        test = Feature(setter=True)

        def _set_test(self, iprop, value):
            self.val = value

        def _pre_set_test(self, iprop, value):
            return value/2

        def _post_set_test(self, iprop, val, i_val, response):
            self.val = (val, i_val)

    o = OverridePreSet()
    o.test = 1
    assert o.val == (1, 0.5)


def test_clone_if_needed():

    prop = Feature(getter=True)

    class Overriding(DummyParent):
        test = prop

        def _get_test(self, iprop):
            return 1

    assert Overriding.test is prop

    class OverridingParent(Overriding):

        def _get_test(self):
            return 2

    assert OverridingParent.test is not prop

# --- Test customizing feature ------------------------------------------------


class ToCustom(DummyParent):

    feat = Feature(getter=True, checks='{aux} is True')

    def __init__(self):
        super(ToCustom, self).__init__()
        self.aux = True
        self.aux2 = True
        self.custom_called = 0

    def _get_feat(self, feat):
        return feat


def test_customizing_append():

    class CustomAppend(ToCustom):

        @append()
        def _pre_get_feat(self, feat):
            self.custom_called += 1
            assert self.aux2 is True

    driver = CustomAppend()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 2


def test_customizing_prepend():

    class CustomPrepend(ToCustom):

        @prepend()
        def _pre_get_feat(self, feat):
            self.custom_called += 1
            assert self.aux2 is True

    driver = CustomPrepend()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 3


def test_customizing_add_after():

    class CustomAddAfter(ToCustom):

        @add_after('checks')
        def _pre_get_feat(self, feat):
            self.custom_called += 1
            assert self.aux2 is True

    driver = CustomAddAfter()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 2


def test_customizing_add_before():

    class CustomAddBefore(ToCustom):

        @add_before('checks')
        def _pre_get_feat(self, feat):
            self.custom_called += 1
            assert self.aux2 is True

    driver = CustomAddBefore()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 3


def test_customizing_replace():

    class CustomReplace(ToCustom):

        @replace('checks')
        def _pre_get_feat(self, feat):
            self.custom_called += 1
            assert self.aux2 is True

    driver = CustomReplace()
    driver.aux = False
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 2


def test_copying_custom_behavior1():

    class CustomAppend(ToCustom):

        @append()
        def _pre_get_feat(self, feat):
            self.custom_called += 1
            assert self.aux2 is True

    class CopyingCustom(CustomAppend):

        feat = set_feat(checks=None)

    driver = CopyingCustom()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    driver.feat
    assert driver.custom_called == 3


def test_copying_custom_behavior2():

    class CustomAddAfter(ToCustom):

        @add_after('checks')
        def _pre_get_feat(self, feat):
            self.custom_called += 1
            assert self.aux2 is True

    class CopyingCustom(CustomAddAfter):

        feat = set_feat(checks=None)

    driver = CopyingCustom()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    driver.feat
    assert driver.custom_called == 3


def test_copying_custom_behavior3():

    class CustomReplace(ToCustom):

        @replace('checks')
        def _pre_get_feat(self, feat):
            self.custom_called += 1
            assert self.aux2 is True

    class CopyingCustom(CustomReplace):

        feat = set_feat(checks=None)

    driver = CopyingCustom()
    assert driver.feat
    assert driver.custom_called == 1

    driver.aux2 = False
    with raises(AssertionError):
        driver.feat
    assert driver.custom_called == 2

    driver.aux2 = True
    driver.aux = False
    driver.feat
    assert driver.custom_called == 3


# --- Test declaring subsystems -----------------------------------------------


def test_subsystem_declaration1():

    class DeclareSubsystem(DummyParent):

        #: Subsystem docstring
        sub_test = subsystem()

    assert DeclareSubsystem.sub_test.__doc__ == 'Subsystem docstring'
    d = DeclareSubsystem()
    assert d.__subsystems__
    assert isinstance(d.sub_test, SubSystem)


def test_subsystem_declaration2():

    class DeclareSubsystem2(DummyParent):

        sub_test = subsystem()
        with sub_test as s:

            #: Subsystem feature doc
            s.test = Feature()

    assert isinstance(DeclareSubsystem2.sub_test.test, Feature)
    assert DeclareSubsystem2.sub_test.test.__doc__ == 'Subsystem feature doc'
    d = DeclareSubsystem2()
    with raises(AttributeError):
        d.sub_test.test


def test_subsystem_declaration3():

    class DeclareSubsystem(DummyParent):

        sub_test = subsystem()
        with sub_test as s:
            s.test = Feature(getter=True)

            @s
            def _get_test(self, instance):
                return True

    d = DeclareSubsystem()
    assert d.sub_test.test


def test_subsystem_declaration4():

    class DeclareSubsystem(DummyParent):

        sub_test = subsystem()

    class Mixin(SubSystem):

        test = Feature(getter=True)

        def _get_test(self, instance):
                return True

    class OverrideSubsystem(DeclareSubsystem):

            sub_test = subsystem(Mixin)

    d = OverrideSubsystem()
    assert d.sub_test.test

# --- Test declaring channels -----------------------------------------------


def test_channel_declaration1():

    class Dummy(Channel):
        pass

    class DeclareChannel(DummyParent):

        ch = channel('_available_ch', Dummy)

        def _available_ch(self):
            return (1,)

    d = DeclareChannel()
    assert d.__channels__
    assert d.ch.available == (1,)
    ch = d.ch[1]
    assert isinstance(ch, Dummy)
    assert d.ch[1] is ch


def test_def_check():
    with raises(NotImplementedError):
        HasFeatures().default_check_operation(None, None, None)


# --- Test cache handling -----------------------------------------------------

class TestHasFeaturesCache(object):

    def setup(self):

        class CacheTest(DummyParent):
            test1 = Feature()
            test2 = Feature()

            ss = subsystem()
            with ss:
                ss.test = Feature()

            ch = channel('list_channels')
            with ch:
                ch.aux = Feature()

            def list_channels(self):
                return [1, 2]

        self.a = CacheTest()
        self.ss = self.a.ss
        self.ch1 = self.a.ch[1]
        self.ch2 = self.a.ch[2]

        self.a._cache = {'test1': 1, 'test2': 2}
        self.ss._cache = {'test': 1}
        self.ch1._cache = {'aux': 1}
        self.ch2._cache = {'aux': 2}

    def test_clear_all_caches(self):

        self.a.clear_cache()
        assert self.a._cache == {}
        assert self.ss._cache == {}
        assert self.ch1._cache == {}
        assert self.ch2._cache == {}

    def test_clear_save_ss(self):

        self.a.clear_cache(False)
        assert self.a._cache == {}
        assert self.ss._cache == {'test': 1}
        assert self.ch1._cache == {}
        assert self.ch2._cache == {}

    def test_clear_save_ch(self):

        self.a.clear_cache(channels=False)
        assert self.a._cache == {}
        assert self.ss._cache == {}
        assert self.ch1._cache == {'aux': 1}
        assert self.ch2._cache == {'aux': 2}

    def test_clear_by_feat(self):

        self.a.clear_cache(features=['test1', 'ch.aux', 'ss.test'])
        assert self.a._cache == {'test2': 2}
        assert self.ss._cache == {}
        assert self.ch1._cache == {}
        assert self.ch2._cache == {}

    def test_check_cache_all_caches(self):
        res = self.a.check_cache()
        assert res == {'test1': 1, 'test2': 2, 'ss': {'test': 1},
                       'ch': {1: {'aux': 1}, 2: {'aux': 2}}}

    def test_check_cache_save_ss(self):
        res = self.a.check_cache(False)
        assert res == {'test1': 1, 'test2': 2,
                       'ch': {1: {'aux': 1}, 2: {'aux': 2}}}

    def test_check_cache_save_ch(self):
        res = self.a.check_cache(channels=False)
        assert res == {'test1': 1, 'test2': 2, 'ss': {'test': 1}}

    def test_check_cache_prop(self):
        res = self.a.check_cache(properties=['test1', 'ss.test', 'ch.aux'])
        assert res == {'test1': 1, 'ss': {'test': 1},
                       'ch': {1: {'aux': 1}, 2: {'aux': 2}}}
