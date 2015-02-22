# -*- coding: utf-8 -*-
"""
    lantz_core.features.feature
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Base descriptor for all instrument properties declaration.

    :copyright: 2015 by Lantz Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)
from types import MethodType
from future.utils import exec_
from inspect import cleandoc
from functools import update_wrapper

from ..errors import LantzError


class Feature(property):
    """Descriptor representing the most basic instrument property.

    Features should not be used outside the definition of a class to avoid
    weird behaviour when some methods are customized.
    Feature are not meant to be used when writing a driver as it is a bit
    bare, one should rather use the more specialised found in other modules
    of the features package.

    When subclassing a Feature a number of rule should be enforced :
    - the subclass should accept all the parameters from the base class
    - all creation arguments must be stored in creation_kwargs. Failing to do
    this will result in the impossibility to use set_feat.

    Parameters
    ----------
    getter : optional
        Object used to access the instrument property value through the use
        of the driver. If absent the Feature will be considered write only.
        This is typically a string. If the default get behaviour is overwritten
        True should be passed to mark the property as readable.
    setter : optional
        Object used to set the instrument property value through the use
        of the driver. If absent the Feature will be considered read-only.
        This is typically a string. If the default set behaviour is overwritten
        True should be passed to mark the property as settable.
    get_format : unicode, optional
        String to use to extract the interesting value from the instrument
        answer.
    retries : int, optional
        Whether or not a failed communication should result in a new attempt
        to communicate after re-opening the communication. The value is used to
        determine how many times to retry.
    checks : unicode or tuple(2)
        Booelan tests to execute before anything else when attempting to get or
        set an iproperty. Multiple assertion can be separated with ';'.
        Instrument values can be referred to using the following syntax :
        {iprop_name}.
        If a single string is provided it is used to run checks before get and
        set, if a tuple of length 2 is provided the first element is used for
        the get operation, the second for the set operation, None can be used
        to indicate no check should be performed.
        The check methods built from this are bound to the get_check and
        set_check names.
    discard : tuple
        Tuple of names of features or limits whose cached value should be
        discarded after setting the Feature.

    Attributes
    ----------
    name : unicode
        Name of the IProperty. This is set by the HasIProps instance and
        should not be manipulated by user code.
    creation_kwargs : dict
        Dictionary in which all the creation args should be stored to allow
        subclass customisation. This should not be manipulated by user code.

    """
    def __init__(self, getter=None, setter=None, get_format='', retries=0,
                 checks=None):
        self._getter = getter
        self._setter = setter
        self._retries = retries
        # Don't create the weak values dict if it is not used.
        self._proxies = ()
        self.creation_kwargs = {'getter': getter, 'setter': setter,
                                'retries': retries, 'checks': checks,
                                'get_format': get_format}

        super(Feature,
              self).__init__(self._get if getter is not None else None,
                             self._set if setter is not None else None,
                             self._del)
        if checks:
            self._build_checkers(checks)
        self.name = ''

    def pre_get(self, instance):
        """Hook to perform checks before querying a value from the instrument.

        If anything goes wrong this method should raise the corresponding
        error.

        Parameters
        ----------
        instance : HasFeatures
            Object on which this Feature is defined.

        """
        pass

    def get(self, instance):
        """Acces the parent driver to retrieve the state of the instrument.

        By default this method falls back to calling the parent
        default_get_feature method. This behaviour can be customized by
        creating a _get_(feat name) method on the driver class.

        Parameters
        ----------
        instance : HasFeatures
            Object on which this Feature is defined.

        Returns
        -------
        value :
            The value as returned by the query method. If any formatting is
            necessary it should be done in the post_get method.

        """
        return instance.default_get_feature(self, self._getter)

    def post_get(self, instance, value):
        """Hook to alter the value returned by the underlying driver.

        This can be used to convert the answer from the instrument to a more
        human friendly representation. By default this is a no-op. This
        behaviour can be customized by creating a _post_get_(feat name) method
        on the driver class.

        Parameters
        ----------
        instance : HasFeatures
            Object on which this Feature is defined.
        value :
            Value as returned by the underlying driver.

        Returns
        -------
        formatted_value :
            Formatted value.

        """
        return value

    def pre_set(self, instance, value):
        """Hook to format the value passed to the Feature before sending it
        to the instrument.

        This can be used to convert the passed value to something easier to
        pass to the instrument. By default this is a no-op. This behaviour can
        be customized by creating a _pre_set_(feat name) method on the driver
        class.

        Parameters
        ----------
        instance : HasFeature
            Object on which this Feature is defined.
        value :
            Value as passed by the user.

        Returns
        -------
        i_value :
            Value which should be passed to the set method.

        """
        return value

    def set(self, instance, value):
        """Access the driver to actually set the instrument state.

        By default this method falls back to calling the parent
        default_set_feature method. This behavior can be customized by
        creating a _set_(feat name) method on the driver class.

        Parameters
        ----------
        instance : HasFeatures
            Object on which this Feature is defined.
        value :
            Object to pass to the driver method to set the value.

        """
        return instance.default_set_feature(self, self._setter, value)

    def post_set(self, instance, value, i_value, response):
        """Hook to perform additional action after setting a value.

        This can be used to check the instrument operated correctly or perform
        some cleanup. By default this falls back on the driver
        default_check_instr_operation method. This behaviour can be customized
        by creating a _post_set_(iprop name) method on the driver class.

        Parameters
        ----------
        instance : HasFeatures
            Object on which this Feature is defined.
        value :
            Value as passed by the user.
        i_value :
            Value which was passed to the set method.
        response :
            Return value of the set method.

        Raises
        ------
        LantzError :
            Raised if the driver detects an issue.

        """
        res, details = instance.default_check_operation(self, value, i_value,
                                                        response)
        if not res:
            mess = 'The instrument did not succeed to set {} to {} ({})'
            if details:
                mess += ':' + str(details)
            else:
                mess += '.'
            raise LantzError(mess.format(self._name, value, i_value))

    def clone(self):
        """Clone the Feature by copying all the local attributes and instance
        methods

        """
        p = self.__class__(self._getter, self._setter, retries=self._retries)
        p.__doc__ = self.__doc__

        for k, v in self.__dict__.items():
            if isinstance(v, MethodType):
                setattr(p, k, MethodType(v.__func__, p))
            else:
                setattr(p, k, v)

        return p

    def make_doc(self, doc):
        """Build a comprehensive docstring from the procided user doc and using
        the configuration of the feature.

        """
        # TODO do
        self.__doc__ = doc

    def extract(self, value):
        """
        """
        # TODO implement
        pass

    def _wrap_with_checker(self, func, target='pre_get'):
        """Wrap a func to execute checker before it if necessary and bind as
        method.

        Parameters
        ----------
        func : callable
            Callable to use as pre_set or pre_get method which should be
            wrapped.
        target : {'pre_get', 'pre_set'}
            Target method to which bind the wrapper.

        """
        if target not in ('pre_get', 'pre_set'):
            mess = cleandoc('''The target of _wrap_with_checker should be
                            pre_set or pre_get, not {}''')
            raise ValueError(mess.format(target))

        func_ = func.__func__ if isinstance(func, MethodType) else func

        if target == 'pre_get' and hasattr(self, 'get_check'):
                def wrapper(self, instance):
                    self.get_check(instance)
                    return func_(self, instance)
                update_wrapper(wrapper, func_)
                func = wrapper
        elif target == 'pre_set' and hasattr(self, 'set_check'):
            def wrapper(self, instance, value):
                self.set_check(instance, value)
                return func_(self, instance, value)
            update_wrapper(wrapper, func_)
            func = wrapper

        if isinstance(func, MethodType):
            if func.__self__ is not self:
                func = MethodType(func.__func__, self)
        else:
            func = MethodType(func, self)

        setattr(self, target, func)

    def _build_discard(self, to_discard):
        """
        """
        # TODO implement
        pass

    def _build_checkers(self, checks):
        """Create the custom check function and bind them to check_get and
        check_set.

        """
        build = self._build_checker
        if len(checks) == 2:
            if checks[0]:
                self.get_check = MethodType(build(checks[0]), self)
                self.pre_get = self.get_check
            if checks[1]:
                self.set_check = MethodType(build(checks[1], True), self)
                self.pre_set = self.set_check
        else:
            self.get_check = MethodType(build(checks), self)
            self.pre_get = self.get_check
            self.set_check = MethodType(build(checks, True), self)
            self.pre_set = self.set_check

    def _build_checker(self, check, set=False):
        """Assemble a checker function from the provided assertions.

        Parameters
        ----------
        check : unicode
            ; separated string containing boolean test to assert. '{' and '}'
            delimit field which should be replaced by instrument state. 'value'
            should be considered a reserved keyword available when checking
            a set operation.

        Returns
        -------
        checker : function
            Function to use

        """
        func_def = 'def check(self, instance):\n' if not set\
            else 'def check(self, instance, value):\n'
        assertions = check.split(';')
        for assertion in assertions:
            # First find replacement fields.
            aux = assertion.split('{')
            if len(aux) < 2:
                # Silently ignore checks unrelated to instrument state.
                continue
            line = 'assert '
            els = [el.strip() for s in aux for el in s.split('}')]
            for i in range(0, len(els), 2):
                e = els[i]
                if i+1 < len(els):
                    line += e + ' getattr(instance, "{}") '.format(els[i+1])
                else:
                    line += e
            values = ', '.join(('getattr(instance,  "{}")'.format(el)
                                for el in els[1::2]))

            val_fmt = ', '.join(('{}'.format(el)+'={}' for el in els[1::2]))
            a_mess = 'assertion {} failed, '.format(' '.join(els).strip())
            a_mess += 'values are : {}".format(self.name, {})'.format(val_fmt,
                                                                      values)

            if set:
                a_mess = '"Setting {} ' + a_mess
            else:
                a_mess = '"Getting {} ' + a_mess

            func_def += '    ' + line + ', ' + a_mess + '\n'

        loc = {}
        exec_(func_def, locs=loc)
        return loc['check']

    def _get(self, instance):
        """Getter defined when the user provides a value for the get arg.

        """
        with instance.lock:
            cache = instance._cache
            name = self.name
            if name in cache:
                return cache[name]

            val = get_chain(self, instance)
            if instance.use_cache:
                cache[name] = val

            return val

    def _set(self, instance, value):
        """Setter defined when the user provides a value for the set arg.

        """
        with instance.lock:
            cache = instance._cache
            name = self.name
            if name in cache and value == cache[name]:
                return

            set_chain(self, instance, value)
            if instance.use_cache:
                cache[name] = value

    def _del(self, instance):
        """Deleter clearing the cache of the instrument for this Feature.

        """
        instance.clear_cache(features=(self.name,))


def get_chain(feat, instance):
    """Generic get chain for Features.

    """
    i = -1
    feat.pre_get(instance)

    while i < feat._retries:
        try:
            i += 1
            val = feat.get(instance)
            break
        except instance.retries_exceptions:
            if i != feat._retries:
                instance.reopen_connection()
                continue
            else:
                raise

    alt_val = feat.post_get(instance, val)

    return alt_val


def set_chain(feat, instance, value):
    """Generic set chain for Features.

    """
    i_val = feat.pre_set(instance, value)
    i = -1
    while i < feat._retries:
        try:
            i += 1
            resp = feat.set(instance, i_val)
            break
        except instance.retries_exceptions:
            if i != feat._retries:
                instance.reopen_connection()
                continue
            else:
                raise
    feat.post_set(instance, value, i_val, resp)
