# -*- coding: utf-8 -*-
"""
    lantz_core.features.mappings
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Module defining a Feature used to deal with 8-bits binary register.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from collections import OrderedDict

from .feature import Feature


class Register(Feature):
    """Property handling a bit field as a mapping.

    Parameters
    ----------
    names : iterable or dict
        Names to associate to each bit fields from 0 to 7. When using an
        iterable None can be used to mark a useless bit. When using a dict
        the values are used to specify the bits to consider.

    """
    def __init__(self, getter=None, setter=None, names=(), extract='',
                 retries=0, checks=None, discard=None):
        Feature.__init__(self, getter, setter, extract, retries,
                         checks, discard)

        if isinstance(names, dict):
            aux = list(range(8))
            for n, i in names.items():
                aux[i] = n
            names = aux

        else:
            names = list(names)
            if len(names) != 8:
                raise ValueError('Register necessitates 8 names')

            # Makes sure every key is unique by using the bit index if None is
            # found
            for i, n in enumerate(names[:]):
                if n is None:
                    names[i] = i

        self.names = tuple(names)
        self.creation_kwargs['names'] = names

        self.modify_behavior('post_get', self.byte_to_dict,
                             ('byte_to_dict', 'prepend'), True)

        self.modify_behavior('pre_set', self.dict_to_byte,
                             ('dict_to_byte', 'append'), True)

    def byte_to_dict(self, instance, value):
        """Convert the byte returned by the instrument to a dict.

        """
        val = int(value)

        def bit_conversion(x, i):
            return bool(x & (1 << i))

        return OrderedDict((n, bit_conversion(val, i))
                           for i, n in enumerate(self.names)
                           if n is not None)

    def dict_to_byte(self, instance, value):
        """Convert a dict into a byte value.

        """
        byte = sum((2**self.names.index(k) for k in value if value[k]))
        return byte
