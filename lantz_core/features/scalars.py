# -*- coding: utf-8 -*-
"""
    lantz_core.features.scalars
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Property for scalars values such float, int, string, etc...

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
# Used to get a 2/3 independent unicode conversion.
from future.builtins import str as ustr

from .enumerable import Enumerable
from .limits_validated import LimitsValidated
from .mapping import Mapping
from ..unit import get_unit_registry, UNIT_SUPPORT

if UNIT_SUPPORT:
    from pint.quantity import _Quantity


class Unicode(Mapping, Enumerable):
    """ Feature casting the instrument answer to a unicode, support
    enumeration.

    """
    def __init__(self, getter=None, setter=None, values=(), mapping=None,
                 extract='', retries=0, checks=None, discard=None):

        if mapping:
            Mapping.__init__(self, getter, setter, mapping, extract,
                             retries, checks, discard)
        else:
            Enumerable.__init__(self, getter, setter, values, extract,
                                retries, checks, discard)

        self.modify_behavior('post_get', self.cast_to_unicode,
                             ('cast_to_unicode', 'append'), True)

    def cast_to_unicode(self, driver, value):
        return ustr(value)


class Int(LimitsValidated, Mapping, Enumerable):
    """ Property casting the instrument answer to an int.

    Support enumeration or range validation (the range takes precedence).

    """
    def __init__(self, getter=None, setter=None, values=(), mapping=None,
                 limits=None, extract='', retries=0, checks=None,
                 discard=None):
        if mapping:
            Mapping.__init__(self, getter, setter, mapping, extract,
                             retries, checks, discard)
        elif values and not limits:
            Enumerable.__init__(self, getter, setter, values, extract,
                                retries, checks, discard)
        else:
            LimitsValidated.__init__(self, getter, setter, limits, extract,
                                     retries, checks, discard)

        self.modify_behavior('post_get', self.cast_to_int,
                             ('cast', 'append'), True)

    def cast_to_int(self, driver, value):
        """Cast the value returned by the instrument to an int.

        """
        return int(value)


class Float(LimitsValidated, Mapping, Enumerable):
    """ Property casting the instrument answer to a float or Quantity.

    Support range validation and unit conversion.

    """
    def __init__(self, getter=None, setter=None, values=(), mapping=None,
                 limits=None, unit=None, extract='', retries=0, checks=None,
                 discard=None):
        if mapping:
            Mapping.__init__(self, getter, setter, mapping, extract,
                             retries, checks, discard)
        elif values and not limits:
            Enumerable.__init__(self, getter, setter, values, extract,
                                retries, checks, discard)
        else:
            LimitsValidated.__init__(self, getter, setter, limits, extract,
                                     retries, checks, discard)

        if UNIT_SUPPORT and unit:
            ureg = get_unit_registry()
            self.unit = ureg.parse_expression(unit)
        else:
            self.unit = None

        self.creation_kwargs.update({'unit': unit, 'values': values,
                                     'limits': limits})

        if UNIT_SUPPORT:
            spec = (('convert', 'add_before', 'validate') if (values or limits)
                    else ('convert', 'prepend'))
            self.modify_behavior('pre_set',  self.convert,
                                 spec, True)

        self.modify_behavior('post_get', self.cast_to_float,
                             ('cast', 'append'), True)

    def cast_to_float(self, driver, value):
        """Cast the value returned by the instrument to float or Quantity.

        """
        fval = float(value)
        if self.unit:
            return fval*self.unit

        else:
            return fval

    def convert(self, driver, value):
        """Convert unit.

        """
        if isinstance(value, _Quantity):
            if self.unit:
                value = value.to(self.unit).magnitude
            else:
                self.unit = value.units
                value = value.magnitude

        return value

    def validate_limits(self, obj, value):
        """Make sure a value is in the given range.

        This method is meant to be used as a pre-set.

        """
        if not self.limits.validate(value, self.unit):
            self.raise_limits_error(value)
        else:
            return value
