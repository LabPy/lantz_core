# -*- coding: utf-8 -*-
"""
    lantz_core.channel
    ~~~~~~~~~~~~~

    Channel simplifies the writing of instrument implementing channel specific
    behaviours.

    :copyright: 2015 by The Lantz Authors
    :license: BSD, see LICENSE for more details.
"""

from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from .has_features import AbstractChannel
from .subsystem import SubSystem


class Channel(SubSystem):
    """Channels are used to represent instrument channels identified by a id
    (a number generally).

    They are similar to SubSystems in that they expose a part of the
    instrument capabilities but multiple instances of the same channel
    can exist at the same time under the condition that they have different
    ids.

    By default channels passes their id to their parent when they call
    default_*_feat as the kwarg 'ch_id' which can be used by the parent
    to direct the call to the right channel.

    Parameters
    ----------
    parent : HasFeat
        Parent object which can be the concrete driver or a subsystem or
        channel.
    id :
        Id of the channel used by the instrument to correctly route the calls.

    Attributes
    ----------
    id :
        Id of the channel used by the instrument to correctly route the calls.

    """
    def __init__(self, parent, id, **kwargs):
        super(Channel, self).__init__(parent, **kwargs)
        self.id = id

    @property
    def lock(self):
        """Access parent lock."""
        return self.parent.lock

    def default_get_feature(self, feat, cmd, *args, **kwargs):
        """Channels simply pipes the call to their parent.

        """
        kwargs['id'] = self.id
        return self.parent.default_get_feature(feat, cmd, *args, **kwargs)

    def default_set_feature(self, feat, cmd, *args, **kwargs):
        """Channels simply pipes the call to their parent.

        """
        kwargs['id'] = self.id
        return self.parent.default_set_feature(feat, cmd, *args, **kwargs)

    def default_check_operation(self, feat, value, i_value, response):
        """Channels simply pipes the call to their parent.

        """
        return self.parent.default_check_operation(feat, value, i_value,
                                                   response)

AbstractChannel.register(Channel)


class ChannelContainer(object):
    """Container storing references to the instrument channels.

    Parameters
    ----------
    cls : class
        Class of the channel to instantiate when a channel is requested.

    parent : HasFeatures
        Reference to the parent object holding the channel.

    name : unicode
        Name of the channel subpart on the parent.

    list_available : unicode
        Name of the parent method to use to query the available channels.

    """

    def __init__(self, cls, parent, name, available):
        self._cls = cls
        self._channels = {}
        self._name = name
        self._parent = parent
        if isinstance(available, (tuple, list)):
            self._list = lambda: available
        else:
            self._list = getattr(parent, available)

    @property
    def available(self):
        """List the available channels.

        """
        return self._list()

    def __getitem__(self, ch_id):
        if ch_id in self._channels:
            return self._channels[ch_id]

        parent = self._parent
        ch = self._cls(parent, ch_id,
                       caching_allowed=parent.use_cache
                       )
        self._channels[ch_id] = ch
        return ch

    def __iter__(self):
        for id in self.available:
            yield self[id]
