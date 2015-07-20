# -*- coding: utf-8 -*-
"""
    lantz_core.features.limits_validated
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Property for scalars values such float, int, string, etc...

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from past.builtins import basestring
from inspect import cleandoc

from .feature import Feature
from ..util import validate_limits
from ..limits import AbstractLimitsValidator


class LimitsValidated(Feature):
    """ Feature checking the given value respects the limits before setting.

    Parameters
    ----------
    range : LimitsValidator or str
        If a LimitsValidator is provided it is used as is, if a string is
        provided it is used to retrieve the range from the driver at runtime.

    """
    def __init__(self, getter=None, setter=None, limits=None, extract='',
                 retries=0, checks=None, discard=None):
        Feature.__init__(self, getter, setter, extract,
                         retries, checks, discard)
        if limits:
            if isinstance(limits, AbstractLimitsValidator):
                self.limits = limits
                validate = self.validate_limits
            elif isinstance(limits, basestring):
                self.limits_id = limits
                validate = self.get_limits_and_validate
            else:
                mess = cleandoc('''The limits kwarg should either be a limits
                    validator or a string used to retrieve the range through
                    get_range''')
                raise TypeError(mess)

            self.modify_behavior('pre_set', validate, ('validate', 'append'),
                                 True)

        self.creation_kwargs['limits'] = limits

    def validate_limits(self, driver, value):
        """Make sure a value is in the given range.

        This method is meant to be used as a pre-set.

        """
        return validate_limits(driver, value, self.limits, self.name)

    def get_limits_and_validate(self, driver, value):
        """Query the current range from the driver and validate the values.

        This method is meant to be used as a pre-set.

        """
        self.limits = driver.get_limits(self.limits_id)
        return self.validate_limits(driver, value)
