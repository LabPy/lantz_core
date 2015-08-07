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
from collections import OrderedDict
from stringparser import Parser

from .util import wrap_custom_feat_method, MethodsComposer, COMPOSERS
from ..errors import LantzError
from ..util import build_checker


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
    extract : unicode or Parser, optional
        String or stringparser.Parser to use to extract the interesting value
        from the instrument answer.
    retries : int, optional
        Whether or not a failed communication should result in a new attempt
        to communicate after re-opening the communication. The value is used to
        determine how many times to retry.
    checks : unicode or tuple(2)
        Booelan tests to execute before anything else when attempting to get or
        set a feature. Multiple assertion can be separated with ';'. The
        driver driver can be accessed under the name driver and in a setter
        the value under the name value, ie the following assertion is correct:
        driver.voltage > value
        If a single string is provided it is used to run checks before get and
        set, if a tuple of length 2 is provided the first element is used for
        the get operation, the second for the set operation, None can be used
        to indicate no check should be performed.
        The check methods built from this are bound to the get_check and
        set_check names.
    discard : tuple or dict
        Tuple of names of features whose cached value should be discarded after
        setting the Feature or dictionary specifying a list of feature whose
        cache should be discarded under the 'feature' key and a list of limits
        to discard under the 'limits' key.

    Attributes
    ----------
    name : unicode
        Name of the Feature. This is set by the HasFeatures driver and
        should not be manipulated by user code.
    creation_kwargs : dict
        Dictionary in which all the creation args should be stored to allow
        subclass customisation. This should not be manipulated by user code.

    """
    def __init__(self, getter=None, setter=None, extract='', retries=0,
                 checks=None, discard=None):
        self._getter = getter
        self._setter = setter
        self._retries = retries
        self._customs = {}
        # Don't create the weak values dict if it is not used.
        self._proxies = ()
        self.creation_kwargs = {'getter': getter, 'setter': setter,
                                'retries': retries, 'checks': checks,
                                'extract': extract, 'discard': discard}

        super(Feature,
              self).__init__(self._get if getter is not None else None,
                             self._set if setter is not None else None,
                             self._del)

        if checks:
            self._build_checkers(checks)
        if discard:
            if not isinstance(discard, dict):
                discard = {'features': discard}
            self._discard = discard
            self.modify_behavior('post_set', self.discard_cache,
                                 ('discard', 'append'), True)

        if extract:
            if isinstance(extract, Parser):
                self._parser = extract
            else:
                self._parser = Parser(extract)
            self.modify_behavior('post_get', self.extract,
                                 ('extract', 'prepend'), True)
        self.name = ''

    def pre_get(self, driver):
        """Hook to perform checks before querying a value from the instrument.

        If anything goes wrong this method should raise the corresponding
        error.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.

        """
        pass

    def get(self, driver):
        """Acces the parent driver to retrieve the state of the instrument.

        By default this method falls back to calling the parent
        default_get_feature method. This behaviour can be customized by
        creating a _get_(feat name) method on the driver class.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.

        Returns
        -------
        value :
            The value as returned by the query method. If any formatting is
            necessary it should be done in the post_get method.

        """
        return driver.default_get_feature(self, self._getter)

    def post_get(self, driver, value):
        """Hook to alter the value returned by the underlying driver.

        This can be used to convert the answer from the instrument to a more
        human friendly representation. By default this is a no-op. This
        behaviour can be customized by creating a _post_get_(feat name) method
        on the driver class.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.
        value :
            Value as returned by the underlying driver.

        Returns
        -------
        formatted_value :
            Formatted value.

        """
        return value

    def pre_set(self, driver, value):
        """Hook to format the value passed to the Feature before sending it
        to the instrument.

        This can be used to convert the passed value to something easier to
        pass to the instrument. By default this is a no-op. This behaviour can
        be customized by creating a _pre_set_(feat name) method on the driver
        class.

        Parameters
        ----------
        driver : HasFeature
            Object on which this Feature is defined.
        value :
            Value as passed by the user.

        Returns
        -------
        i_value :
            Value which should be passed to the set method.

        """
        return value

    def set(self, driver, value):
        """Access the driver to actually set the instrument state.

        By default this method falls back to calling the parent
        default_set_feature method. This behavior can be customized by
        creating a _set_(feat name) method on the driver class.

        Parameters
        ----------
        driver : HasFeatures
            Object on which this Feature is defined.
        value :
            Object to pass to the driver method to set the value.

        """
        return driver.default_set_feature(self, self._setter, value)

    def post_set(self, driver, value, i_value, response):
        """Hook to perform additional action after setting a value.

        This can be used to check the instrument operated correctly or perform
        some cleanup. By default this falls back on the driver
        default_check_operation method. This behaviour can be customized
        by creating a _post_set_(feat name) method on the driver class.

        Parameters
        ----------
        driver : HasFeatures
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
        self.check_operation(driver, value, i_value, response)

    def check_operation(self, driver, value, i_value, response):
        """Check the instrument operated correctly.

        This uses the driver default_check_operation method.

        Parameters
        ----------
        driver : HasFeatures
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
        res, details = driver.default_check_operation(self, value, i_value,
                                                      response)
        if not res:
            mess = 'The instrument did not succeed to set {} to {} ({})'
            if details:
                mess += ':' + str(details)
            else:
                mess += '.'
            raise LantzError(mess.format(self.name, value, i_value))

    def discard_cache(self, driver, value, i_value, response):
        """Empty the cache of the specified values.

        """
        if 'features' in self._discard:
            driver.clear_cache(features=self._discard['features'])
        if 'limits' in self._discard:
            driver.discard_limits(self._discard['limits'])

    def extract(self, driver, value):
        """Extract the return value using the extract value.

        """
        return self._parser(value)

    def clone(self):
        """Clone the Feature by copying all the local attributes and driver
        methods

        """
        p = self.__class__(self._getter, self._setter, retries=self._retries)
        p.__doc__ = self.__doc__

        for k, v in self.__dict__.items():
            if isinstance(v, MethodType):
                setattr(p, k, MethodType(v.__func__, p))
            elif isinstance(v, MethodsComposer):
                setattr(p, k, v.clone())
            elif isinstance(v, dict):
                setattr(p, k, v.copy())
            else:
                setattr(p, k, v)

        return p

    def make_doc(self, doc):
        """Build a comprehensive docstring from the provided user doc and using
        the configuration of the feature.

        """
        # TODO do
        self.__doc__ = doc

    def modify_behavior(self, method_name, custom_method, specifiers=(),
                        internal=False):
        """Alter the behavior of the Feature using the provided method.

        Those operations are logged into the _customs dictionary in OrderedDict
        for each method so that they can be duplicated by copy_custom_behaviors
        The storing format is as follow : method, name of the operation, args
        of the operation.

        Parameters
        ----------
        method_name : unicode
            Name of the Feature behavior which should be modified.

        custom_method : callable|None
            Method to use when customizing the feature behavior, or None when
            removing a customization.

        specifiers : tuple, optional
            Tuple used to determine how the method should be used. If ommitted
            the method will simply replace the existing behavior otherwise
            it will be used to update the MethodComposer in the adequate
            fashion. For get and set MethodComposers are not used and no matter
            this value the method will replace the existing behavior.
            ex : ('custom', 'add_after', 'old')

        internal : bool, optional
            Private flag used to indicate that this method is used for internal
            purposes and that the modification makes no sense to remember as
            this won't have to be copied by copy_custom_behaviors.

        """
        # Make the method a method of the Feature.
        # The if clause handles the case of 'remove' for which passing None
        # should work
        m = (wrap_custom_feat_method(custom_method, self) if custom_method
             else None)

        # In the absence of specifiers or for get and set we simply replace the
        # method.
        if method_name in ('get', 'set') or not specifiers:
            setattr(self, method_name, m)
            if not internal:
                self._customs[method_name] = m
            return

        # Otherwise we make sure we have a MethopsComposer.
        composer = getattr(self, method_name)
        if not isinstance(composer, MethodsComposer):
            composer = COMPOSERS[method_name]()

        # In case of non internal modifications (ie unrelated to Feature
        # initialisation) we keep a description of what has been done to be
        # able to copy those behaviors. If a method already existed we assume
        # it was meaningful and add it in the composer under the id 'old'.
        if not internal:
            if method_name not in self._customs:
                self._customs[method_name] = OrderedDict()
            elif not isinstance(self._customs[method_name], OrderedDict):
                old = self._customs[method_name]
                composer.prepend('old', old)
                self._customs[method_name] = OrderedDict(old=(old, 'prepend'))

        # We now update the composer.
        composer_method_name = specifiers[1]
        composer_method = getattr(composer, composer_method_name)
        if composer_method_name in ('add_before', 'add_after'):
            composer_method(specifiers[2], specifiers[0], m)
        elif composer_method_name == 'remove':
            composer_method(specifiers[0])
        else:
            composer_method(specifiers[0], m)

        # Finally we update the _customs dict and reassign the composer.
        setattr(self, method_name, composer)
        if not internal:
            customs = self._customs[method_name]
            if composer_method_name == 'remove':
                del customs[specifiers[0]]
            elif composer_method_name == 'replace':
                if specifiers[0] in customs:
                    old = list(customs[specifiers[0]])
                    old[0] = m
                    customs[specifiers[0]] = tuple(old)
                else:
                    ind = composer._names.index(specifiers[0])
                    if ind == 0:
                        customs[specifiers[0]] = (m, 'prepend')
                    else:
                        n = composer._names[ind-1]
                        customs[specifiers[0]] = (m, 'add_after', n)
            else:
                op = [m] + list(specifiers[1:])
                self._customs[method_name][specifiers[0]] = tuple(op)

    def copy_custom_behaviors(self, feat):
        """Copy the custom behaviors existing on a feature to this one.

        This is used by set_feat to preserve the custom behaviors after
        recreating the feature with different kwargs. If an add_before or
        add_after clause cannot be satisfied because the anchor disappeared
        this method tries to insert the custom method in the most likely
        position.

        CAUTION : This method strives to build something that makes sense but
        it will most likely fail in some weird corner cases so avoid as mush as
        possible to use set_feat on feature modified using specially named
        method on the driver.

        """
        # Loop on methods which are affected by mofifiers.
        for meth_name, modifiers in feat._customs.items():
            if isinstance(modifiers, MethodType):
                    self.modify_behavior(meth_name, modifiers)
                    continue

            # Loop through all the modifications.
            for custom, modifier in modifiers.items():

                method = getattr(self, meth_name)
                # In the absence of anchor we simply attempt the operation.
                if modifier[1] not in ('add_after', 'add_before'):
                    self.modify_behavior(meth_name, modifier[0],
                                         (custom, modifier[1]))
                elif not isinstance(method, MethodsComposer):
                    aux = {'add_after': 'append', 'add_before': 'prepend'}
                    self.modify_behavior(meth_name, modifier[0],
                                         (custom, aux[modifier[1]]))

                # Otherwise we check whether or not the anchor exists and if
                # not try to find the most meaningfull one.
                else:
                    our_names = method._names
                    if modifier[2] in our_names:
                        self.modify_behavior(meth_name, modifier[0],
                                             (custom, modifier[1],
                                              modifier[2]))
                    else:
                        feat_names = getattr(feat, meth_name)._names
                        # For add after we try to find an entry existing in
                        # both feature going backward (we will prepend at the
                        # worst), for add before we go forward (we will append
                        # in the absence of match).
                        shift = -1 if modifier[1] == 'add_after' else -1
                        index = feat_names.index(custom)
                        while index > 0 and index < len(feat_names)-1:
                            index += shift
                            name = feat_names[index]
                            if name in our_names:
                                self.modify_behavior(meth_name, modifier[0],
                                                     (custom, modifier[1],
                                                      name))
                                shift = 0
                                break

                        if shift != 0:
                            op = 'prepend' if shift == -1 else 'append'
                            self.modify_behavior(meth_name, modifier[0],
                                                 (custom, op))

    def _build_checkers(self, checks):
        """Create the custom check function and bind them to check_get and
        check_set.

        """
        build = build_checker
        if len(checks) != 2:
            checks = (checks, checks)

        if checks[0]:
            self.get_check = MethodType(build(checks[0], '(self, driver)'),
                                        self)
        if checks[1]:
            self.set_check = MethodType(build(checks[1],
                                              '(self, driver, value)',
                                              'value'),
                                        self)

        if hasattr(self, 'get_check'):
            self.modify_behavior('pre_get', self.get_check,
                                 ('checks', 'prepend'), True)
        if hasattr(self, 'set_check'):
            self.modify_behavior('pre_set', self.set_check,
                                 ('checks', 'prepend'), True)

    def _get(self, driver):
        """Getter defined when the user provides a value for the get arg.

        """
        with driver.lock:
            cache = driver._cache
            name = self.name
            if name in cache:
                return cache[name]

            val = get_chain(self, driver)
            if driver.use_cache:
                cache[name] = val

            return val

    def _set(self, driver, value):
        """Setter defined when the user provides a value for the set arg.

        """
        with driver.lock:
            cache = driver._cache
            name = self.name
            if name in cache and value == cache[name]:
                return

            set_chain(self, driver, value)
            if driver.use_cache:
                cache[name] = value

    def _del(self, driver):
        """Deleter clearing the cache of the instrument for this Feature.

        """
        driver.clear_cache(features=(self.name,))


def get_chain(feat, driver):
    """Generic get chain for Features.

    """
    i = -1
    feat.pre_get(driver)

    while i < feat._retries:
        try:
            i += 1
            val = feat.get(driver)
            break
        except driver.retries_exceptions:
            if i != feat._retries:
                driver.reopen_connection()
                continue
            else:
                raise

    alt_val = feat.post_get(driver, val)

    return alt_val


def set_chain(feat, driver, value):
    """Generic set chain for Features.

    """
    i_val = feat.pre_set(driver, value)
    i = -1
    while i < feat._retries:
        try:
            i += 1
            resp = feat.set(driver, i_val)
            break
        except driver.retries_exceptions:
            if i != feat._retries:
                driver.reopen_connection()
                continue
            else:
                raise
    feat.post_set(driver, value, i_val, resp)
