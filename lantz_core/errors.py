# -*- coding: utf-8 -*-
"""
    lantz_core.errors
    ~~~~~~~~~~~~

    Implements base classes for instrumentation related exceptions. They are
    useful to mix with specific exceptions from libraries or modules and
    therefore allowing code to catch them via lantz excepts without
    breaking specific ones.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""


class LantzError(Exception):
    """Base class for all Lantz errors.

    """
    pass


class InvalidCommand(LantzError):
    pass


class TimeoutError(LantzError):
    pass


class InterfaceNotSupported(LantzError):
    pass
