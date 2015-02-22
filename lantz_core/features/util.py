# -*- coding: utf-8 -*-
"""
    lantz_core.features.util
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Tools to customize feature and help in their writings.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from collections import OrderedDict


class MethodComposer(object):
    """
    """
    __slots__ = ('methods', '_iter')

    def __init__(self, ):
        self.methods = OrderedDict()

    def prepend(self, name, method):
        """
        """
        pass

    def append(self, name, method):
        """
        """
        pass

    def add_after(self, anchor, name, method):
        """
        """
        pass

    def add_before(self, anchor, name, method):
        """
        """
        pass

    def replace(self, name, method):
        """
        """
        pass

    def reset(self):
        """
        """
        pass

    def _rebuild(self):
        """
        """
        self._iter = self.methods.values()


def PreGetComposer(MethodComposer):
    """
    """
    def __call__(self, driver):
        """
        """
        for m in self._iter:
            m(driver)


def PostGetComposer(MethodComposer):
    """
    """
    def __call__(self, driver, value):
        """
        """
        for m in self._iter:
            value = m(driver, value)
        return value


def PreSetComposer(MethodComposer):
    """
    """
    def __call__(self, driver, value):
        """
        """
        for m in self._iter:
            value = m(driver, value)
        return m


def PostSetComposer(MethodComposer):
    """
    """
    def __call__(self, driver, value, d_value, response):
        for m in self._iter:
            value = m(driver, value, d_value, response)
