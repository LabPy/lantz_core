# -*- coding: utf-8 -*-
"""
    tests.test_subsystem
    ~~~~~~~~~~~~~~~~~~~~~~~

    Test basic subsystem instance functionalities.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from nose.tools import assert_equal, assert_is

from lantz_core.has_features import subsystem
from .testing_tools import DummyParent


class SSParent(DummyParent):

    ss = subsystem()


def test_ss_d_get():

    a = SSParent()
    a.ss.default_get_feature(None, 'Test', 1, a=2)
    assert_equal(a.d_get_called, 1)
    assert_equal(a.d_get_cmd, 'Test')
    assert_equal(a.d_get_args, (1,))
    assert_equal(a.d_get_kwargs, {'a': 2})


def test_ss_d_set():
    a = SSParent()
    a.ss.default_set_feature(None, 'Test', 1, a=2)
    assert_equal(a.d_set_called, 1)
    assert_equal(a.d_set_cmd, 'Test')
    assert_equal(a.d_set_args, (1,))
    assert_equal(a.d_set_kwargs, {'a': 2})


def test_ss_d_check():
    a = SSParent()
    a.ss.default_check_operation(None, None, None, None)
    assert_equal(a.d_check_instr, 1)


def test_ss_lock():
    a = SSParent()
    assert_is(a.ss.lock, a.lock)


def test_ss_reop():
    a = SSParent()
    a.ss.reopen_connection()
    assert_equal(a.ropen_called, 1)
