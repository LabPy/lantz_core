# -*- coding: utf-8 -*-
"""
    lantz_core.features.bool
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Feature for values requiring a mapping between user and instrs values.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from .mapping import Mapping


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
                 extract='', retries=0, checks=None, discard=None, ):
        Mapping.__init__(self, getter, setter, mapping, extract,
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
