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

from .testing_tools import TestingParent


def test_documenting_feature():

    class DocTester(TestingParent):

        #: This is the docstring for
        #: the Feature test.
        test = Feature()

    assert DocTester.test.__doc__ ==\
        'This is the docstring for the Feature test.'

# --- Test overriding features behaviors --------------------------------------


def test_customizing():

    class DecorateIP(Feature):

        def __init__(self, getter=True, setter=True, retries=0,
                     get_format=None, checks=None, dec='<br>'):
            super(DecorateIP, self).__init__(getter, setter)
            self.dec = dec

        def post_get(self, iprop, val):
            return self.dec+val+self.dec

    class ParentTester(TestingParent):
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

    class NoOverrideGet(TestingParent):
        test = Feature(getter=True)

    assert NoOverrideGet().test

    class OverrideGet(TestingParent):
        test = Feature(getter=True)

        def _get_test(self, iprop):
            return 'This is a test'

    assert OverrideGet().test == 'This is a test'


def test_overriding_pre_get():

    class OverridePreGet(TestingParent):
        test = Feature(getter=True)

        def _get_test(self, iprop):
            return 'this is a test'

        def _pre_get_test(self, iprop):
            assert False

    with raises(AssertionError):
        OverridePreGet().test


def test_overriding_post_get():

    class OverridePostGet(TestingParent):
        test = Feature(getter=True)

        def _get_test(self, iprop):
            return 'this is a test'

        def _post_get_test(self, iprop, val):
            return '<br>'+val+'<br>'

    assert OverridePostGet().test == '<br>this is a test<br>'


def test_overriding_set():

    class NoOverrideSet(TestingParent):
        test = Feature(setter=True)

    NoOverrideSet().test = 1

    class OverrideSet(TestingParent):
        test = Feature(setter=True)

        def _set_test(self, iprop, value):
            self.val = value

    o = OverrideSet()
    o.test = 1
    assert o.val == 1


def test_overriding_pre_set():

    class OverridePreSet(TestingParent):
        test = Feature(setter=True)

        def _set_test(self, iprop, value):
            self.val = value

        def _pre_set_test(self, iprop, value):
            return value/2

    o = OverridePreSet()
    o.test = 1
    assert o.val == 0.5


def test_overriding_post_set():

    class OverridePreSet(TestingParent):
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

    class Overriding(TestingParent):
        test = prop

        def _get_test(self, iprop):
            return 1

    assert Overriding.test is prop

    class OverridingParent(Overriding):

        def _get_test(self):
            return 2

    assert OverridingParent.test is not prop

# --- Test declaring subsystems -----------------------------------------------


def test_subsystem_declaration1():

    class DeclareSubsystem(TestingParent):

        #: Subsystem docstring
        sub_test = subsystem()

    assert DeclareSubsystem.sub_test.__doc__ == 'Subsystem docstring'
    d = DeclareSubsystem()
    assert d.__subsystems__
    assert isinstance(d.sub_test, SubSystem)


def test_subsystem_declaration2():

    class DeclareSubsystem2(TestingParent):

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

    class DeclareSubsystem(TestingParent):

        sub_test = subsystem()
        with sub_test as s:
            s.test = Feature(getter=True)

            @s
            def _get_test(self, instance):
                return True

    d = DeclareSubsystem()
    assert d.sub_test.test


def test_subsystem_declaration4():

    class DeclareSubsystem(TestingParent):

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

    class DeclareChannel(TestingParent):

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
