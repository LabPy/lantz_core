# -*- coding: utf-8 -*-
"""
    tests.test_action
    ~~~~~~~~~~~~~~~~~

    Module dedicated to testing action behavior.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pytest import mark

from lantz_core.action import Action
from lantz_core.unit import UNIT_SUPPORT, get_unit_registry
from .testing_tools import DummyParent


def test_action_without_unit():
    """Test defining an action not using units conversions.

    """
    class Dummy(DummyParent):

        @Action()
        def test(self):
            return type(self)

    assert isinstance(Dummy.test, Action)

    dummy = Dummy()
    assert dummy.test() is Dummy


@mark.skipif(UNIT_SUPPORT is False, reason="Requires Pint")
def test_action_with_unit():
    """Test defining an action not using units conversions.

    """
    class Dummy(DummyParent):

        @Action(units=('ohm*A', (None, 'ohm', 'A')))
        def test(self, r, i):
            return r*i

    assert isinstance(Dummy.test, Action)

    dummy = Dummy()
    assert dummy.test(2, 3) == get_unit_registry().parse_expression('6 V')
