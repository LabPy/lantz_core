# -*- coding: utf-8 -*-
"""
    lantz_core.features
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Feature are descriptor used for implementing instrument properties.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from .bool import Bool
from .scalars import Unicode, Int, Float
from .register import Register

__all__ = ['Bool', 'Unicode', 'Int', 'Float', 'Register']
