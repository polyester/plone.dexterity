# -*- coding: utf-8 -*-
from copy import deepcopy
from datetime import datetime
from persistent import Persistent

from dateutil.tz import tzlocal
from plone.behavior.interfaces import IBehaviorAssignable
from zope.annotation import IAttributeAnnotatable
from zope.container.contained import Contained
from zope.container.ordered import OrderedContainer
from zope.interface import implementer
from zope.interface.declarations import Implements
from zope.interface.declarations import ObjectSpecificationDescriptor
from zope.interface.declarations import getObjectSpecification
from zope.interface.declarations import implementedBy
from zope.schema.interfaces import IContextAwareDefaultFactory
from plone.dexterity.interfaces import IDexterityContainer
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.interfaces import IDexterityItem
from plone.dexterity.schema import SCHEMA_CACHE
from plone.uuid.interfaces import IAttributeUUID
from plone.uuid.interfaces import IUUID

_marker = object()
_zone = tzlocal()


def _default_from_schema(context, schema, fieldname):
    """helper to lookup default value of a field
    """
    if schema is None:
        return _marker
    field = schema.get(fieldname, None)
    if field is None:
        return _marker
    if IContextAwareDefaultFactory.providedBy(
            getattr(field, 'defaultFactory', None)
    ):
        bound = field.bind(context)
        return deepcopy(bound.default)
    else:
        return deepcopy(field.default)


class FTIAwareSpecification(ObjectSpecificationDescriptor):
    """A __providedBy__ decorator that returns the interfaces provided by
    the object, plus the schema interface set in the FTI.
    """

    def __get__(self, inst, cls=None):  # noqa
        # We're looking at a class - fall back on default
        if inst is None:
            return getObjectSpecification(cls)

        direct_spec = getattr(inst, '__provides__', None)

        # avoid recursion - fall back on default
        if getattr(self, '__recursion__', False):
            return direct_spec

        spec = direct_spec

        # If the instance doesn't have a __provides__ attribute, get the
        # interfaces implied by the class as a starting point.
        if spec is None:
            spec = implementedBy(cls)

        # Find the data we need to know if our cache needs to be invalidated
        portal_type = getattr(inst, 'portal_type', None)

        # If the instance has no portal type, then we're done.
        if portal_type is None:
            return spec

        # Find the cached value. This calculation is expensive and called
        # hundreds of times during each request, so we require a fast cache
        cache = getattr(inst, '_v__providedBy__', None)

        # See if we have a current cache. Reasons to do this include:
        #
        #  - The FTI was modified.
        #  - The instance was modified and persisted since the cache was built.
        #  - The instance has a different direct specification.
        updated = (
            inst._p_mtime,
            SCHEMA_CACHE.modified(portal_type),
            SCHEMA_CACHE.invalidations,
            hash(direct_spec)
        )
        if cache is not None and cache[:-1] == updated:
            if cache[-1] is not None:
                return cache[-1]
            return spec

        main_schema = SCHEMA_CACHE.get(portal_type)
        if main_schema:
            dynamically_provided = [main_schema]
        else:
            dynamically_provided = []

        # block recursion
        self.__recursion__ = True
        try:
            assignable = IBehaviorAssignable(inst, None)
            if assignable is not None:
                for behavior_registration in assignable.enumerateBehaviors():
                    if behavior_registration.marker:
                        dynamically_provided.append(
                            behavior_registration.marker
                        )
        finally:
            del self.__recursion__

        if not dynamically_provided:
            # rare case if no schema nor behaviors with markers are set
            inst._v__providedBy__ = updated + (None, )
            return spec

        dynamically_provided.append(spec)
        all_spec = Implements(*dynamically_provided)
        inst._v__providedBy__ = updated + (all_spec, )

        return all_spec


@implementer(
    IDexterityContent,
    IAttributeAnnotatable,
    IAttributeUUID
)
class DexterityContent(Persistent, Contained):
    """Base class for Dexterity content
    """

    __providedBy__ = FTIAwareSpecification()

    # portal_type is set by the add view and/or factory
    portal_type = None

    def __init__(  # noqa
            self,
            id=None,
            **kwargs):

        if id is not None:
            self.id = id
        now = datetime.now(tz=_zone)
        self.creation_date = now
        self.modification_date = now

        for (k, v) in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        # python basics:  __getattr__ is only invoked if the attribute wasn't
        # found by __getattribute__
        #
        # optimization: sometimes we're asked for special attributes
        # such as __conform__ that we can disregard (because we
        # wouldn't be in here if the class had such an attribute
        # defined).
        # also handle special dynamic providedBy cache here.
        if name.startswith('__') or name == '_v__providedBy__':
            raise AttributeError(name)

        # attribute was not found; try to look it up in the schema and return
        # a default
        value = _default_from_schema(
            self,
            SCHEMA_CACHE.get(self.portal_type),
            name
        )
        if value is not _marker:
            return value

        # do the same for each subtype
        assignable = IBehaviorAssignable(self, None)
        if assignable is not None:
            for behavior_registration in assignable.enumerateBehaviors():
                if behavior_registration.interface:
                    value = _default_from_schema(
                        self,
                        behavior_registration.interface,
                        name
                    )
                    if value is not _marker:
                        return value

        raise AttributeError(name)

    # Let __name__ and id be identical. Note that id must be ASCII in Zope 2,
    # but __name__ should be unicode. Note that setting the name to something
    # that can't be encoded to ASCII will throw a UnicodeEncodeError

    def _get__name__(self):
        return self.id

    def _set__name__(self, value):
        if isinstance(value, str):
            value = str(value)  # may throw, but that's OK - id must be ASCII
        self.id = value

    __name__ = property(_get__name__, _set__name__)

    def UID(self):
        """Returns the item's globally unique id."""
        return IUUID(self)



@implementer(IDexterityItem)
class Item(DexterityContent):
    """A non-containerish, CMFish item
    """

    __providedBy__ = FTIAwareSpecification()

    # Be explicit about which __getattr__ to use
    __getattr__ = DexterityContent.__getattr__


@implementer(IDexterityContainer)
class Container(OrderedContainer, DexterityContent):
    """Base class for folderish items
    """

    __providedBy__ = FTIAwareSpecification()

    def __init__(self, id=None, **kwargs):
        OrderedContainer.__init__(self)
        DexterityContent.__init__(self, id, **kwargs)

    def __getattr__(self, name):
        try:
            return DexterityContent.__getattr__(self, name)
        except AttributeError:
            value = OrderedContainer.get(self, name, _marker)
            if value is _marker:
                raise
            return value
