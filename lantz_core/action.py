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

from past.builtins import basestring
from functools import update_wrapper, partial
from types import MethodType

from funcsigs import signature

from .limits import IntLimitsValidator, FloatLimitsValidator
from .unit import UNIT_SUPPORT, get_unit_registry
from .util import (build_checker, validate_in, validate_limits,
                   get_limits_and_validate)


class Action(object):
    """Wraps a method with pre and post processing operations.

    All parameters must be passed as keyword arguments.

    All public driver methods should be decorated as an Action to make them
    easy to identify and hence make instrospection easier.

    Parameters
    ----------
    units : tuple, optional
        Tuple of length 2 containing the return unit and the unit of each
        passed argument. None can be used to mark that an argument should not
        be converted. The first argument (self) should always be marked this
        way.

    checks : unicode, optional
        Booelan tests to execute before calling the function. Multiple
        assertions can be separated with ';'. All the methods argument are
        available in the assertion execution namespace so one can access to the
        driver using self and to the arguments using their name (the signature
        of the wrapper is made to match the signature of the wrapped method).

    values : dict, optional
        Dictionary mapping the arguments names to their allowed values.

    limits : dict, optional
        Dictionary mapping the arguments names to their allowed limits. Limits
        can a be a tuple of length 2, or 3 (min, max, step) or the name of
        the limits to use to check the input.

    Notes
    -----
    A single argument should be value checked or limit checked but not both,
    unit conversion is performed before anything else. When limit validating
    against a driver limits the parameter should ALWAYS be converted to the
    same unit as the one used by the limits.

    """
    def __init__(self, **kwargs):

        self.kwargs = kwargs

    def __call__(self, func):
        update_wrapper(self, func)
        self.sig = signature(func)
        self.func = self.decorate(func, self.kwargs)
        return self

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return MethodType(self.func, obj)

    def decorate(self, func, kwargs):
        """Decorate a function according to passed arguments.

        Override this function to alter how

        """
        if 'limits' in kwargs or 'values' in kwargs:
            func = self.add_values_limits_validation(func,
                                                     kwargs.get('values', {}),
                                                     kwargs.get('limits', {})
                                                     )

        if 'checks' in kwargs:
            func = self.add_checks(func, kwargs['checks'])

        if UNIT_SUPPORT and 'units' in kwargs:
            func = self.add_unit_support(func, kwargs['units'])

        return func

    def add_unit_support(self, func, units):
        """Wrap a func using Pint to automatically convert Quantity.

        """
        ureg = get_unit_registry()
        return ureg.wraps(*units, strict=False)(func)

    def add_checks(self, func, checks):
        """Build a checker function and use it to decorate func.

        Parameters
        ----------
        func : callable
            Function to decorate.

        checks : unicode
            ; separated string of expression to assert.

        Returns
        -------
        wrapped : callable
            Function wrapped with the assertion checks.

        """
        check = build_checker(checks, self.sig)

        def check_wrapper(*args, **kwargs):
            check(*args, **kwargs)
            return func(*args, **kwargs)
        update_wrapper(check_wrapper, func)
        return check_wrapper

    def add_values_limits_validation(self, func, values, limits):
        """Add arguments validation to call.

        Parameters
        ----------
        func : callable
            Function to decorate.

        values : dict
            Dictionary mapping the parameters name to the set of allowed
            values.

        limits : dict
            Dictionary mapping the parameters name to the limits they must
            abide by.

        units : dict
            Dictionary mapping

        Returns
        -------
        wrapped : callable
            Function wrapped with the parameters validation.

        """
        validators = {}
        for name, vals in values.items():
            validators[name] = partial(validate_in, name=name,
                                       values=set(vals))

        for name, lims in limits.items():
            if name in validators:
                msg = 'Arg %s can be limits or values validated not both'
                raise ValueError(msg % name)
            if isinstance(lims, (list, tuple)):
                if any([isinstance(e, float) for e in lims]):
                    l = FloatLimitsValidator(*lims)
                else:
                    l = IntLimitsValidator(*lims)

                validators[name] = partial(validate_limits, limits=l,
                                           name=name)

            elif isinstance(lims, basestring):
                validators[name] = partial(get_limits_and_validate,
                                           limits=lims, name=name)

            else:
                msg = 'Invalid type for limits values (key {}) : {}'
                raise TypeError(msg.format(name, type(lims)))

        sig = self.sig

        def wrapper(*args, **kwargs):

            bound = sig.bind(*args, **kwargs).arguments
            driver = args[0]
            for n in validators:
                validators[n](driver, bound[n])

            return func(*args, **kwargs)

        update_wrapper(wrapper, func)
        return wrapper
