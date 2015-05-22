# -*- coding: utf-8 -*-
"""
    lantz_core.util
    ~~~~~~~~~~~~~~~

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from future.utils import exec_
from future.builtins import str


def build_checker(checks, signature, ret=''):
    """Assemble a checker function from the provided assertions.

    Parameters
    ----------
    checks : unicode
        ; separated string containing boolean test to assert. '{' and '}'
        delimit field which should be replaced by instrument state.

    signature : unicode or funcsigs.Signature
        Signature of the check function to build.

    ret : unicode
        Name of the parameters to return. This string will be preceded by a
        return statement.

    Returns
    -------
    checker : function
        Function to use

    """
    func_def = 'def check' + str(signature) + ':\n'
    assertions = checks.split(';')
    for assertion in assertions:
        # XXXX use AST manipulation to provide more infos about assertion
        # failure. Take inspiration from pytest.assertions.rewrite.
        a_mess = '"Assertion %s failed"' % assertion
        func_def += '    assert ' + assertion + ', ' + a_mess + '\n'

    if ret:
        func_def += '    return %s' % ret

    loc = {}
    exec_(func_def, globals(), loc)
    return loc['check']


# The next three function take all driver as first argument for homogeneity.

def validate_in(driver, value, values, name):
    """Assert that a value is in a container.

    """
    if value not in values:
        mess = 'Allowed value for {} are {}, {} not allowed'
        raise ValueError(mess.format(name, values, value))
    return value


def validate_limits(driver, value, limits, name):
    """Make sure a value is in the given range.

    """
    if not limits.validate(value):
        raise_limits_error(name, value, limits)
    else:
        return value


def get_limits_and_validate(driver, value, limits, name):
    """Query the current limits from the driver and validate the values.

    """
    limits = driver.get_limits(limits)
    return validate_limits(driver, value, limits, name)


def raise_limits_error(name, value, limits):
    """Raise a value when the limits validation fails.

    """
    mess = 'The provided value {} is out of bound for {}.'
    mess = mess.format(value, name)
    if limits.minimum:
        mess += ' Minimum {}.'.format(limits.minimum)
    if limits.maximum:
        mess += ' Maximum {}.'.format(limits.maximum)
    if limits.step:
        mess += ' Step {}.'.format(limits.step)
    raise ValueError(mess)
