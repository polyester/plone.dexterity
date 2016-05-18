# -*- coding: utf-8 -*-
from copy import deepcopy
from datetime import datetime
from dateutil.tz import tzlocal
from persistent import Persistent
from plone.behavior.interfaces import IBehaviorAssignable
from plone.dexterity.interfaces import IDexterityContainer
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.interfaces import IDexterityItem
from plone.dexterity.interfaces import READ_PERMISSIONS_KEY
from plone.dexterity.schema import SCHEMA_CACHE
from plone.dexterity.utils import all_merged_tagged_values_dict
from plone.dexterity.utils import iterSchemata
from plone.dexterity.utils import safe_str
from plone.uuid.interfaces import IAttributeUUID
from plone.uuid.interfaces import IUUID
from zope.annotation import IAttributeAnnotatable
from zope.component import queryUtility
from zope.container.contained import Contained
from zope.container.ordered import OrderedContainer
from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.interface import implementer
from zope.interface.declarations import getObjectSpecification
from zope.interface.declarations import implementedBy
from zope.interface.declarations import Implements
from zope.interface.declarations import ObjectSpecificationDescriptor
from zope.location.interfaces import IContained
from zope.schema.interfaces import IContextAwareDefaultFactory
from zope.security.interfaces import IPermission
from zope.securitypolicy import zopepolicy


_marker = object()
_zone = tzlocal()
FLOOR_DATE = datetime(1970, 1, 1)  # always effective
CEILING_DATE = datetime(2500, 1, 1)  # never expires


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


class AttributeValidator(object):
    """Decide whether attributes should be accessible. This is set as the
    __allow_access_to_unprotected_subobjects__ variable in Dexterity's content
    classes.
    """

    def __call__(self, name, value):
        # Short circuit for things like views or viewlets
        if name == '':
            return 1

        context = IContained(self).__parent__

        # we may want to cache this based on the combined mod-times
        # of fti and context, but even this is not save in the case someone
        # decides to have behaviors bound on something different than context
        # or fti, i.e. schemas for subtrees.
        protection_dict = all_merged_tagged_values_dict(
                iterSchemata(context),
                READ_PERMISSIONS_KEY
        )

        if name not in protection_dict:
            return 1

        permission = queryUtility(IPermission, name=protection_dict[name])
        if permission is not None:
            policy = zopepolicy.ZopeSecurityPolicy()
            return policy.checkPermission(permission.title, context)

        return 0


@implementer(
    IDexterityContent,
    IAttributeAnnotatable,
    IAttributeUUID,
    IWriteZopeDublinCore,
)
class DexterityContent(Persistent, Contained):
    """Base class for Dexterity content
    """

    __providedBy__ = FTIAwareSpecification()
    __allow_access_to_unprotected_subobjects__ = AttributeValidator()

    # portal_type is set by the add view and/or factory
    portal_type = None

    title = u''
    description = u''
    subject = ()
    creators = ()
    contributors = ()
    effective_date = None
    expiration_date = None
    format = 'text/html'
    language = ''
    rights = ''

    def __init__(  # noqa
            self,
            id=None, title=_marker, subject=_marker, description=_marker,
            contributors=_marker, effective_date=_marker,
            expiration_date=_marker, format=_marker, language=_marker,
            rights=_marker, **kwargs):

        if id is not None:
            self.id = id
        now = datetime.utcnow()
        self.creation_date = now
        self.modification_date = now

        if title is not _marker:
            self.setTitle(title)
        if subject is not _marker:
            self.setSubject(subject)
        if description is not _marker:
            self.setDescription(description)
        if contributors is not _marker:
            self.setContributors(contributors)
        if effective_date is not _marker:
            self.setEffectiveDate(effective_date)
        if expiration_date is not _marker:
            self.setExpirationDate(expiration_date)
        if format is not _marker:
            self.setFormat(format)
        if language is not _marker:
            self.setLanguage(language)
        if rights is not _marker:
            self.setRights(rights)

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

    def notifyModified(self):
        """Update creators and modification_date.

        This is called from CMFCatalogAware.reindexObject.
        """
        self.addCreator()
        self.setModificationDate()

    def addCreator(self, creator=None):
        """ Add creator to Dublin Core creators.
        """
        if len(self.creators) > 0:
            # do not add creator if one is already set
            return

        if creator is None:
            return

        # call self.listCreators() to make sure self.creators exists
        if creator and creator not in self.listCreators():
            self.creators = self.creators + (creator, )

    def setModificationDate(self, modification_date=None):
        """ Set the date when the resource was last modified.

        When called without an argument, sets the date to now.
        """
        if modification_date is None:
            self.modification_date = datetime.now()
        else:
            self.modification_date = modification_date

    # IMinimalDublinCore

    def Title(self):
        return self.title or ''

    def Description(self):
        return self.description or ''

    def Type(self):
        ti = self.getTypeInfo()
        return ti is not None and ti.Title() or 'Unknown'

    # IDublinCore

    def listCreators(self):
        # List Dublin Core Creator elements - resource authors.
        if self.creators is None:
            return ()
        return self.creators

    def Creator(self):
        # Dublin Core Creator element - resource author.
        creators = self.listCreators()
        return creators and creators[0] or ''

    def Subject(self):
        # Dublin Core Subject element - resource keywords.
        if self.subject is None:
            return ()
        return self.subject

    def Publisher(self):
        # Dublin Core Publisher element - resource publisher.
        return 'No publisher'

    def listContributors(self):
        # Dublin Core Contributor elements - resource collaborators.
        return self.contributors

    def Contributors(self):
        # Deprecated alias of listContributors.
        return self.listContributors()

    def Date(self, zone=None):
        # Dublin Core Date element - default date.
        if zone is None:
            zone = _zone
        # Return effective_date if set, modification date otherwise
        date = getattr(self, 'effective_date', None)
        if date is None:
            date = self.modified()
        try:
            return date.astimezone(zone).isoformat()
        except (TypeError, ValueError):
            return date.isoformat()

    def CreationDate(self, zone=None):
        # Dublin Core Date element - date resource created.
        if zone is None:
            zone = _zone
        # return unknown if never set properly
        if self.creation_date:
            try:
                return self.creation_date.astimezone(zone).isoformat()
            except (TypeError, ValueError):
                return self.creation_date.isoformat()
        else:
            return 'Unknown'

    def EffectiveDate(self, zone=None):
        # Dublin Core Date element - date resource becomes effective.
        if zone is None:
            zone = _zone
        if getattr(self, 'effective_date', None):
            try:
                return self.effective_date.astimezone(zone).isoformat()
            except (TypeError, ValueError):
                return self.effective_date.isoformat()
        else:
            return None

    def ExpirationDate(self, zone=None):
        # Dublin Core Date element - date resource expires.
        if zone is None:
            zone = _zone
        if getattr(self, 'expiration_date', None):
            try:
                return self.expiration_date.astimezone(zone).isoformat()
            except (TypeError, ValueError):
                return self.expiration_date.isoformat()
        else:
            return None

    def ModificationDate(self, zone=None):
        # Dublin Core Date element - date resource last modified.
        if zone is None:
            zone = _zone
        try:
            return self.modified().astimezone(zone).isoformat()
        except (TypeError, ValueError):
            return self.modified().isoformat()

    def Identifier(self):
        # Dublin Core Identifier element - resource ID.
        return self.absolute_url()

    def Language(self):
        # Dublin Core Language element - resource language.
        return self.language

    def Rights(self):
        # Dublin Core Rights element - resource copyright.
        return self.rights

    # ICatalogableDublinCore

    def created(self):
        # Dublin Core Date element - date resource created.
        # allow for non-existent creation_date, existed always
        date = getattr(self, 'creation_date', None)
        return date is None and FLOOR_DATE or date

    def effective(self):
        # Dublin Core Date element - date resource becomes effective.
        date = getattr(self, 'effective_date', _marker)
        if date is _marker:
            date = getattr(self, 'creation_date', None)
        return date is None and FLOOR_DATE or date

    def expires(self):
        # Dublin Core Date element - date resource expires.
        date = getattr(self, 'expiration_date', None)
        return date is None and CEILING_DATE or date

    def modified(self):
        # Dublin Core Date element - date resource last modified.
        date = self.modification_date
        if date is None:
            # Upgrade.
            date = datetime.fromtimestamp(self._p_mtime)
            self.modification_date = date
        return date

    def isEffective(self, date):
        # Is the date within the resource's effective range?
        pastEffective = (
            self.effective_date is None or self.effective_date <= date)
        beforeExpiration = (
            self.expiration_date is None or self.expiration_date >= date)
        return pastEffective and beforeExpiration

    # IMutableDublinCore

    def setTitle(self, title):
        # Set Dublin Core Title element - resource name.
        self.title = safe_str(title)

    def setDescription(self, description):
        # Set Dublin Core Description element - resource summary.
        self.description = safe_str(description)

    def setCreators(self, creators):
        # Set Dublin Core Creator elements - resource authors.
        if isinstance(creators, str):
            creators = [creators]
        self.creators = tuple(safe_str(c.strip()) for c in creators)

    def setSubject(self, subject):
        # Set Dublin Core Subject element - resource keywords.
        if isinstance(subject, str):
            subject = [subject]
        self.subject = tuple(safe_str(s.strip()) for s in subject)

    def setContributors(self, contributors):
        # Set Dublin Core Contributor elements - resource collaborators.
        if isinstance(contributors, str):
            contributors = contributors.split(';')
        self.contributors = tuple(
                safe_str(c.strip()) for c in contributors)

    def setEffectiveDate(self, effective_date):
        # Set Dublin Core Date element - date resource becomes effective.
        self.effective_date = effective_date

    def setExpirationDate(self, expiration_date):
        # Set Dublin Core Date element - date resource expires.
        self.expiration_date = expiration_date

    def setFormat(self, format):
        # Set Dublin Core Format element - resource format.
        self.format = format

    def setLanguage(self, language):
        # Set Dublin Core Language element - resource language.
        self.language = language

    def setRights(self, rights):
        # Set Dublin Core Rights element - resource copyright.
        self.rights = safe_str(rights)


@implementer(IDexterityItem)
class Item(DexterityContent):
    """A non-containerish, CMFish item
    """

    __providedBy__ = FTIAwareSpecification()
    __allow_access_to_unprotected_subobjects__ = AttributeValidator()

    # Be explicit about which __getattr__ to use
    __getattr__ = DexterityContent.__getattr__


@implementer(IDexterityContainer)
class Container(OrderedContainer, DexterityContent):
    """Base class for folderish items
    """

    __providedBy__ = FTIAwareSpecification()
    __allow_access_to_unprotected_subobjects__ = AttributeValidator()

    # Make sure PortalFolder's accessors and mutators don't take precedence
    Title = DexterityContent.Title
    setTitle = DexterityContent.setTitle
    Description = DexterityContent.Description
    setDescription = DexterityContent.setDescription

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


def reindexOnModify(content, event):
    """When an object is modified, re-index it in the catalog
    """

    if event.object is not content:
        return

    # NOTE: We are not using event.descriptions because the field names may
    # not match index names.

    # content.reindexObject()
