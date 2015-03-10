# -*- coding: utf-8 -*-
"""
    lantz_core.unit
    ~~~~~~~~~~~~~~~

    Unit handling is done using the Pint library. If absent the unit support is
    simply disabled.

    This module allows the user to specify the UnitRegistry to be used by Lantz
    and exposes some useful Pint features.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

import logging

UNIT_SUPPORT = True

try:
    from pint import UnitRegistry
except ImportError:
    UNIT_SUPPORT = False


UNIT_REGISTRY = None


def set_unit_registry(unit_registry):
    """Set the UnitRegistry used by Lantz.

    Given that conversion can only happen for units declared in the same
    UnitRegistry an application should only use a single registry. This method
    should be called before doing anything else in Lantz (even importing driver
    ) to avoid the creation of a default registry by Eapii.

    Parameters
    ----------
    unit_registry : UnitRegistry
        UnitRegistry to use for Lantz.

    Raises
    ------
    ValueError:
        If a unit registry has already been set.

    """
    global UNIT_REGISTRY
    if UNIT_REGISTRY:
        mess = 'The unit registry used by Lantz cannot be changed once set.'
        raise ValueError(mess)

    UNIT_REGISTRY = unit_registry


def get_unit_registry():
    """Access the UnitRegistry currently in use by Lantz.

    If no UnitRegistry has been previously declared using `set_unit_registry`,
    a new UnitRegistry  is created.

    """
    global UNIT_REGISTRY
    if not UNIT_REGISTRY:
        logger = logging.getLogger(__name__)
        logger.debug('Creating default UnitRegistry for Lantz')
        UNIT_REGISTRY = UnitRegistry()

    return UNIT_REGISTRY
