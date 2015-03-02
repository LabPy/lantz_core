# -*- coding: utf-8 -*-
"""
    tests.test_subsystem
    ~~~~~~~~~~~~~~~~~~~~~~~

    Test basic channel instance functionalities.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from nose.tools import assert_equal, assert_is

from lantz_core.has_features import channel
from .testing_tools import DummyParent


class ChParent(DummyParent):

    ch = channel('_list_ch')

    def _list_ch(self):
        return (1, )


def test_ch_d_get():

    a = ChParent()
    ch = a.ch[1]
    ch.default_get_feature(None, 'Test', 1, a=2)
    assert_equal(a.d_get_called, 1)
    assert_equal(a.d_get_cmd, 'Test')
    assert_equal(a.d_get_args, (1,))
    assert_equal(a.d_get_kwargs, {'ch_id': 1, 'a': 2})


def test_ch_d_set():

    a = ChParent()
    ch = a.ch[1]
    ch.default_set_feature(None, 'Test', 1, a=2)
    assert_equal(a.d_set_called, 1)
    assert_equal(a.d_set_cmd, 'Test')
    assert_equal(a.d_set_args, (1,))
    assert_equal(a.d_set_kwargs, {'ch_id': 1, 'a': 2})


def test_ch_d_check():

    a = ChParent()
    ch = a.ch[1]
    ch.default_check_operation(None, None, None, None)
    assert_equal(a.d_check_instr, 1)


def test_ch_lock():
    a = ChParent()
    ch = a.ch[1]
    assert_is(ch.lock, a.lock)


def test_ch_reop():
    a = ChParent()
    ch = a.ch[1]
    ch.reopen_connection()
    assert_equal(a.ropen_called, 1)
