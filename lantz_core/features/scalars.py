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
from future.utils import istext
from inspect import cleandoc

from .feature import Feature
from ..limits import AbstractLimitsValidator
from ..unit import get_unit_registry, UNIT_SUPPORT

if UNIT_SUPPORT:
    from pint.quantity import _Quantity


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


class Unicode(Enumerable):
    """ Feature casting the instrument answer to a unicode, support
    enumeration.

    """
    def __init__(self, getter=None, setter=None, values=(), get_format='',
                 retries=0, checks=None, discard=None):
        super(Unicode, self).__init__(getter, setter, values, get_format,
                                      retries, checks, discard)

        self.modify_behavior('post_get', self.cast_to_unicode,
                             ('cast_to_unicode', 'append'), True)

    def cast_to_unicode(self, instance, value):
        return ustr(value)


class LimitsValidated(Feature):
    """ Feature checking the given value respects the limits before setting.

    Parameters
    ----------
    range : LimitsValidator or str
        If a LimitsValidator is provided it is used as is, if a string is
        provided it is used to retrieve the range from the driver at runtime.

    """
    def __init__(self, getter=None, setter=None, limits=None, get_format='',
                 retries=0, checks=None, discard=None):
        super(LimitsValidated, self).__init__(getter, setter, get_format,
                                              retries, checks, discard)
        if limits:
            if isinstance(limits, AbstractLimitsValidator):
                self.limits = limits
                validate = self.validate_limits
            elif istext(limits):
                self.limits_id = limits
                validate = self.get_limits_and_validate
            else:
                mess = cleandoc('''The range kwarg should either be a range
                    validator or a string used to retrieve the range through
                    get_range''')
                raise TypeError(mess)

            self.modify_behavior('pre_set', validate, ('validate', 'append'),
                                 True)

        self.creation_kwargs['range'] = range

    def validate_limits(self, obj, value):
        """Make sure a value is in the given range.

        This method is meant to be used as a pre-set.

        """
        if not self.limits.validate(value):
            self.raise_limits_error(value)
        else:
            return value

    def get_limits_and_validate(self, obj, value):
        """Query the current range from the driver and validate the values.

        This method is meant to be used as a pre-set.

        """
        self.limits = obj.get_limits(self.limits_id)
        return self.validate_limits(obj, value)

    def raise_limits_error(self, value):
        """Raise a value when the limits validation fails.

        """
        mess = 'The provided value {} is out of bound for {}.'
        mess = mess.format(value, self.name)
        lim = self.limits
        if lim.minimum:
            mess += ' Minimum {}.'.format(lim.minimum)
        if lim.maximum:
            mess += ' Maximum {}.'.format(lim.maximum)
        if lim.step:
            mess += ' Step {}.'.format(lim.step)
        raise ValueError(mess)


class Int(LimitsValidated, Enumerable):
    """ Property casting the instrument answer to an int.

    Support enumeration or range validation (the range takes precedence).

    """
    def __init__(self, getter=None, setter=None, values=(), limits=None,
                 get_format='', retries=0, checks=None, discard=None):
        if values and not limits:
            Enumerable.__init__(self, getter, setter, values, get_format,
                                retries, checks, discard)
        else:
            super(Int, self).__init__(getter, setter, limits, get_format,
                                      retries, checks, discard)

        self.modify_behavior('post_get', self.cast_to_int,
                             ('cast', 'append'), True)

    def cast_to_int(self, instance, value):
        """Cast the value returned by the instrument to an int.

        """
        return int(value)


class Float(LimitsValidated, Enumerable):
    """ Property casting the instrument answer to a float or Quantity.

    Support range validation and unit conversion.

    """
    def __init__(self, getter=None, setter=None, values=(), limits=None,
                 unit=None, get_format='', retries=0, checks=None,
                 discard=None):
        if values and not limits:
            Enumerable.__init__(self, getter, setter, values, get_format,
                                retries, checks, discard)
        else:
            super(Float, self).__init__(getter, setter, limits, get_format,
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

    def cast_to_float(self, instance, value):
        """Cast the value returned by the instrument to float or Quantity.

        """
        fval = float(value)
        if self.unit:
            return fval*self.unit

        else:
            return fval

    def convert(self, instance, value):
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
