# -*- coding: utf-8 -*-
"""
    lantz_core.features.mappings
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
    def __init__(self, getter=None, setter=None, mapping=None, get_format='',
                 retries=0, checks=None, discard=None):
        Feature.__init__(self, getter, setter, get_format, retries,
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

    def reverse_map_value(self, instance, value):
        return self._imap[value]

    def map_value(self, instance, value):
        return self._map[value]


class Bool(Mapping):
    """ Boolean property.

    True/False are mapped to the mapping values, aliases can also be declared
    to accept non-boolean values.

    Parameters
    ----------
    aliases : dict, optional
        Keys should be True and False and values the list of aliases.

    """
    def __init__(self, getter=None, setter=None, mapping=None, aliases=None,
                 get_format='', retries=0, checks=None, discard=None, ):
        Mapping.__init__(self, getter, setter, mapping, get_format,
                         retries, checks, discard)

        self._aliases = {True: True, False: False}
        if aliases:
            for k in aliases:
                for v in aliases[k]:
                    self._aliases[v] = k
        self.creation_kwargs['aliases'] = aliases

    def map_value(self, instance, value):
        self._aliases[value]
        return self._map[self._aliases[value]]
