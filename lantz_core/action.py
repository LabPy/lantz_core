# -*- coding: utf-8 -*-
"""
    lantz.action
    ~~~~~~~~~~~~

    Implements the Action class to wrap public driver bound methods.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from functools import update_wrapper
from types import MethodType

from .unit import UNIT_SUPPORT, get_unit_registry

# XXXX implements checks, values, limits
class Action(object):
    """Wraps a method with pre and post processing operations.

    By default only unit processing is supported. Subclass this object to
    customize the behavior.

    All public driver methods should be decorated as an Action to make them
    easy to identify and hence make instrospection easier.

    Paremeters
    ----------
    units : tuple
        Tuple of length 2 containing the return unit and the unit of each
        passed argument. None can be used to mark that an argument should not
        be converted. The first argument (self) should always be marked this
        way.

    checks : unicode
        Booelan tests to execute before anything else. Multiple assertion can
        be separated with ';'. The driver can be accessed using the following
        syntax : {driver}. The arguments can be directly accessed using their
        name.

    values : dict
        Dictionary mapping the arguments names to their allowed values.

    limits : dict
        Dictionary mapping the arguments names to their allowed limits. Limits
        can a be a tuple of length 2, or 3 (min, max, step) or the name of
        the limits to use to check the input.

    Notes
    -----
    A single argument should be value checked or limit checked but not both,
    unit conversion is performed before anything else.

    """
    __slots__ = ('func', 'kwargs', 'driver')

    def __init__(self, **kwargs):

        self.kwargs = kwargs
        self.driver = None

    def __call__(self, func):
        update_wrapper(self, func)
        self.func = self.decorate(func, self.kwargs)
        return self

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return MethodType(self.func, obj, objtype)

    def decorate(self, func, kwargs):
        """Decorate a function according to passed arguments.

        Override this function to alter how

        """
        if UNIT_SUPPORT and 'units' in kwargs:
            return self.add_unit_support(func, kwargs['units'])

        return func

    def add_unit_support(self, func, units):
        """Wrap a func using Pint to automatically convert Quantity.

        """
        ureg = get_unit_registry()
        return ureg.wraps(*units, strict=False)(func)
