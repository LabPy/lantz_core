# -*- coding: utf-8 -*-
"""
    tests.features.test_register
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Module dedicated to testing the register feature.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from pytest import raises

from lantz_core.features.register import Register


class TestRegister(object):

    def test_init(self):
        with raises(ValueError):
            Register('a', names=(None,))

    def test_post_get(self):
        r = Register('a', names=('a', 'b', None, 'r', None, None, None, None))
        byte = r.post_get(None, '10')
        assert len(byte) == 8
        assert byte['b'] and byte['r']
        assert not byte['a']
        assert not byte[2]

    def test_pre_set(self):
        r = Register('a', names={'a': 0, 'b': 1, 'r': 3})
        assert r.pre_set(None, {'a': True, 'b': False}) == 1
