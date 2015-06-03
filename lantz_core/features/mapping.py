# -*- coding: utf-8 -*-
"""
    lantz_core.features.mapping
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Feature for values requiring a mapping between user and instrs values.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from .feature import Feature


class Mapping(Feature):
    """ Feature using a dict to map user input to instrument and back.

    Parameters
    ----------
    mapping : dict or tuple
        Mapping between the user values and instrument values. If a tuple is
        provided the first element should be the mapping between user values
        and instrument input, the second between instrument output and user
        values. This allows to handle asymetric case in which the instrument
        expect a command (ex: CMD ON) but when queried return 1.

    """
    def __init__(self, getter=None, setter=None, mapping=None, extract='',
                 retries=0, checks=None, discard=None):
        Feature.__init__(self, getter, setter, extract, retries,
                         checks, discard)

        mapping = mapping if mapping else {}
        if isinstance(mapping, (tuple, list)):
            self._map = mapping[0]
            self._imap = mapping[1]
        else:
            self._map = mapping
            self._imap = {v: k for k, v in mapping.items()}
        self.creation_kwargs['mapping'] = mapping

        self.modify_behavior('post_get', self.reverse_map_value,
                             ('reverse_map', 'append'), True)

        self.modify_behavior('pre_set', self.map_value,
                             ('map', 'append'), True)

    def reverse_map_value(self, driver, value):
        return self._imap[value]

    def map_value(self, driver, value):
        return self._map[value]
