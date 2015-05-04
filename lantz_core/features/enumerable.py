# -*- coding: utf-8 -*-
"""
    lantz_core.features.enumerable
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Property for scalars values such float, int, string, etc...

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from .feature import Feature


class Enumerable(Feature):
    """ Validate the set value against a finite set of allowed ones.

    Parameters
    ----------
    values : iterable, optional
        Permitted values for the property.

    """
    def __init__(self, getter=None, setter=None, values=(), get_format='',
                 retries=0, checks=None, discard=None):
        super(Enumerable, self).__init__(getter, setter, get_format, retries,
                                         checks, discard)
        self.values = set(values)
        self.creation_kwargs['values'] = values

        if values:
            self.modify_behavior('pre_set', self.validate_in,
                                 ('validate', 'append'), True)

    def validate_in(self, instance, value):
        """Check the provided values is in the supported values.

        """
        if value not in self.values:
            mess = 'Allowed value for {} are {}, {} not allowed'
            raise ValueError(mess.format(self.name, self.values, value))

        return value
