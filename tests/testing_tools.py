# -*- coding: utf-8 -*-
"""
    tests.testing_tools
    ~~~~~~~~~~~~~~~~~~~

    Module defining some common tools for testing lantz_core.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from threading import RLock

from lantz_core.has_features import HasFeatures


class TestingParent(HasFeatures):

    def __init__(self):
        super(TestingParent, self).__init__()
        self.d_get_called = 0
        self.d_get_cmd = None
        self.d_get_args = ()
        self.d_get_kwargs = {}
        self.d_set_called = 0
        self.d_set_cmd = None
        self.d_get_args = ()
        self.d_get_kwargs = {}
        self.d_check_instr = 0
        self.ropen_called = 0
        self.lock = RLock()

    def default_get_feature(self, feat, cmd, *args, **kwargs):
        self.d_get_called += 1
        self.d_get_cmd = cmd
        self.d_get_args = args
        self.d_get_kwargs = kwargs
        return cmd

    def default_set_feature(self, feat, cmd, *args, **kwargs):
        self.d_set_called += 1
        self.d_set_cmd = cmd
        self.d_set_args = args
        self.d_set_kwargs = kwargs

    def default_check_operation(self, feat, value, i_value, response):
        self.d_check_instr += 1
        return True, None

    def reopen_connection(self):
        self.ropen_called += 1
