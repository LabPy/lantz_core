# -*- coding: utf-8 -*-
"""
    tests.features.test_limits_validated.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for the LimitsValidated helper class.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import pytest

from lantz_core.features.limits_validated import LimitsValidated
from lantz_core.limits import IntLimitsValidator

from ..testing_tools import DummyParent


def test_with_no_limits():
    """Test having no limits.

    """
    feat = LimitsValidated(setter=True)
    assert feat.pre_set(None, 1) == 1


def test_with_validator():
    """Test creating a LimitsValidated by passing it a validator.

    """
    feat = LimitsValidated(setter=True, limits=IntLimitsValidator(0, 10))
    assert feat.pre_set(None, 1) == 1
    with pytest.raises(ValueError):
        feat.pre_set(None, -1)


def test_with_name():
    """Test creating a LimitsValidated querying the limit by name.

    """
    class LimitsHolder(DummyParent):

        n = 0

        def _limits_test(self):
            self.n += 1
            return IntLimitsValidator(self.n)

    o = LimitsHolder()
    i = LimitsValidated(setter=True, limits='test')
    assert i.pre_set(o, 1)
    with pytest.raises(ValueError):
        i.pre_set(o, 0)
    o.discard_limits(('test', ))
    with pytest.raises(ValueError):
        i.pre_set(o, 1)


def test_type_error_handling():
    """Test handling of bad type of limits.

    """
    with pytest.raises(TypeError):
        LimitsValidated(setter=True, limits=(1, 2))
