# -*- coding: utf-8 -*-
"""
    tests.features.test_mappings
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Module dedicated to testing the mappings features.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from lantz_core.features.mappings import Mapping, Bool


def test_mapping():
    m = Mapping(mapping={'On': 1, 'Off': 2})
    assert m.post_get(None, 1) == 'On'
    assert m.post_get(None, 2) == 'Off'

    assert m.pre_set(None, 'On') == 1
    assert m.pre_set(None, 'Off') == 2


def test_mapping_asymetric():
    m = Mapping(mapping=({'On': 'ON', 'Off': 'OFF'}, {'1': 'On', '0': 'Off'}))
    assert m.post_get(None, '1') == 'On'
    assert m.post_get(None, '0') == 'Off'

    assert m.pre_set(None, 'On') == 'ON'
    assert m.pre_set(None, 'Off') == 'OFF'


def test_bool():
    b = Bool(mapping={True: 1, False: 2},
             aliases={True: ['On', 'on', 'ON'], False: ['Off', 'off', 'OFF']})
    assert b.pre_set(None, 'ON') == 1
    assert b.pre_set(None, 'off') == 2
