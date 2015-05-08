# -*- coding: utf-8 -*-
"""
    lantz_core.subsystem
    ~~~~~~~~~~~~~~~~~~~~

    Subsystems can be used to give a hierarchical organisation to a driver.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from future.utils import with_metaclass

from .has_features import HasFeaturesMeta, HasFeatures, AbstractSubSystem


class DeclarationMeta(HasFeaturesMeta):
    """Metaclass used to avoid creating an instance in classes declaration.

    """
    def __call__(self, *args, **kwargs):
        """ Create a new instance only if a parent is passed as first argument.

        """
        if not args:
            return self
        else:
            return super(DeclarationMeta, self).__call__(*args, **kwargs)


class SubSystem(with_metaclass(DeclarationMeta, HasFeatures)):
    """SubSystem allow to split the implementation of a driver into multiple
    parts.

    This mechanism allow to avoid crowding the instrument namespace with very
    long Feature names.

    Attributes
    ----------
    parent : HasFeatures
        Parent object of the subsystem.

    """
    def __init__(self, parent, **kwargs):
        super(SubSystem, self).__init__(**kwargs)
        self.parent = parent

    @property
    def lock(self):
        """Access to parent lock."""
        return self.parent.lock

    def reopen_connection(self):
        """Subsystems simply pipes the call to their parent.

        """
        self.parent.reopen_connection()

    def default_get_feature(self, feat, cmd, *args, **kwargs):
        """Subsystems simply pipes the call to their parent.

        """
        return self.parent.default_get_feature(feat, cmd, *args, **kwargs)

    def default_set_feature(self, feat, cmd, *args, **kwargs):
        """Subsystems simply pipes the call to their parent.

        """
        return self.parent.default_set_feature(feat, cmd, *args, **kwargs)

    def default_check_operation(self, feat, value, i_value, response):
        """Subsystems simply pipes the call to their parent.

        """
        return self.parent.default_check_operation(feat, value, i_value,
                                                   response)

AbstractSubSystem.register(SubSystem)
