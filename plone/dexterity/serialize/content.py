# -*- coding: utf-8 -*-
from plone.dexterity.interfaces import IDexterityContainer
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import iterSchemata
from plone.dexterity.utils import iterSchemataForType
from plone.dexterity.utils import resolveDottedName
from plone.jsonserializer.interfaces import IFieldSerializer
from plone.jsonserializer.interfaces import IFieldsetSerializer
from plone.jsonserializer.interfaces import ISchemaSerializer
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.jsonserializer.interfaces import ISerializeToJsonSummary
from plone.jsonserializer.serializer.converters import json_compatible
from plone.server.browser import get_physical_path
from plone.supermodel.interfaces import FIELDSETS_KEY
from plone.supermodel.interfaces import READ_PERMISSIONS_KEY
from plone.supermodel.utils import mergedTaggedValueDict
from plone.supermodel.utils import sortedFields
from zope.component import adapter
from zope.component import ComponentLookupError
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.interface import implementer
from zope.interface import Interface
from zope.schema import getFields
from zope.security.interfaces import IInteraction
from zope.security.interfaces import IPermission


@implementer(ISerializeToJson)
@adapter(IDexterityContent, Interface)
class SerializeToJson(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.permission_cache = {}

    def __call__(self):
        parent = self.context.__parent__
        if parent is not None:
            try:
                parent_summary = getMultiAdapter(
                    (parent, self.request), ISerializeToJsonSummary)()
            except ComponentLookupError:
                parent_summary = {}
        else:
            parent_summary = {}

        result = {
            '@id': '/'.join(get_physical_path(self.context)),
            '@type': self.context.portal_type,
            'parent': parent_summary,
            'created': json_compatible(self.context.creation_date),
            'modified': json_compatible(self.context.modification_date),
            'UID': self.context.UID(),
        }

        for schema in iterSchemata(self.context):

            read_permissions = mergedTaggedValueDict(schema, READ_PERMISSIONS_KEY)

            for name, field in getFields(schema).items():

                if not self.check_permission(read_permissions.get(name)):
                    continue
                serializer = queryMultiAdapter(
                    (field, self.context, self.request),
                    IFieldSerializer)
                value = serializer()
                result[json_compatible(name)] = value

        return result

    def check_permission(self, permission_name):
        if permission_name is None:
            return True

        if permission_name not in self.permission_cache:
            permission = queryUtility(IPermission,
                                      name=permission_name)
            if permission is None:
                self.permission_cache[permission_name] = True
            else:
                security = IInteraction(self.request)
                self.permission_cache[permission_name] = bool(
                    security.checkPermission(permission.title, self.context))
        return self.permission_cache[permission_name]


@implementer(ISerializeToJson)
@adapter(IDexterityContainer, Interface)
class SerializeFolderToJson(SerializeToJson):

    def __call__(self):
        result = super(SerializeFolderToJson, self).__call__()

        # TODO create objectValues on DX
        result['items'] = [
            getMultiAdapter((member, self.request), ISerializeToJsonSummary)()
            for ident, member in self.context.items()
            if not ident.startswith('_')
        ]
        return result


@implementer(ISerializeToJson)
@adapter(IDexterityFTI, Interface)
class SerializeFTIToJson(SerializeToJson):

    def __call__(self):
        fti = self.context
        result = {
            # '@context': 'http://www.w3.org/ns/hydra/context.jsonld',
            'title': fti.id,
            'type': 'object',
            'properties': {
                'fieldsets': {},
                'schemas': {}
            },
        }

        for schema in iterSchemataForType(fti.id):

            schema_serializer = getMultiAdapter(
                (schema, fti, self.request), ISchemaSerializer)
            result['properties']['schemas'][schema_serializer.name] = schema_serializer()

            fieldsets = schema.queryTaggedValue(FIELDSETS_KEY, [])
            fieldset_fields = set()
            for fieldset in fieldsets:
                fields = fieldset.fields
                # Keep a list so we can figure out what doesn't belong
                # to a fieldset
                fieldset_fields.update(fields)

                # Write the fieldset and any fields it contains
                fieldset_serializer = getMultiAdapter(
                    (fieldset, schema, fti, self.request), IFieldsetSerializer)
                result['properties']['fieldsets'][fieldset_serializer.name] = fieldset_serializer()

            # Handle any fields that aren't part of a fieldset
            non_fieldset_fields = [name for name, field in sortedFields(schema)
                                   if name not in fieldset_fields]

            for fieldName in non_fieldset_fields:
                field = schema[fieldName]
                serializer = getMultiAdapter((field, schema, fti, self.request), IFieldSerializer)
                result['properties'][fieldName] = serializer()


            invariants = []
            for i in schema.queryTaggedValue('invariants', []):
                invariants.append("%s.%s" % (i.__module__, i.__name__))
            result['properties']['invariants'] = invariants

        return result


# @implementer(ISerializeToJson)
# @adapter(IDexterityFTI, Interface)
# class SerializeFTIToJson(SerializeToJson):

# from z3c.form.interfaces import IDataManager
# from z3c.form.interfaces import IManagerValidator
# from zExceptions import BadRequest
# from plone.jsonserializer.deserializer import json_body
# from plone.jsonserializer.interfaces import IDeserializeFromJson
# from plone.jsonserializer.interfaces import IFieldDeserializer
# from plone.supermodel.interfaces import WRITE_PERMISSIONS_KEY
# from zope.event import notify
# from zope.lifecycleevent import ObjectModifiedEvent
# from zope.schema.interfaces import ValidationError

# @implementer(IDeserializeFromJson)
# @adapter(IDexterityContent, Interface)
# class DeserializeFromJson(object):
#     def __init__(self, context, request):
#         self.context = context
#         self.request = request

#         self.sm = zopepolicy.ZopeSecurityPolicy()

#         self.permission_cache = {}

#     def __call__(self, validate_all=False):
#         data = json_body(self.request)

#         modified = False
#         schema_data = {}
#         errors = []

#         for schema in iterSchemata(self.context):
#             write_permissions = mergedTaggedValueDict(
#                 schema, WRITE_PERMISSIONS_KEY)

#             for name, field in getFields(schema).items():

#                 field_data = schema_data.setdefault(schema, {})

#                 if field.readonly:
#                     continue

#                 if name in data:
#                     dm = queryMultiAdapter((self.context, field), IDataManager)
#                     if not dm.canWrite():
#                         continue

#                     if not self.check_permission(write_permissions.get(name)):
#                         continue

#                     # Deserialize to field value
#                     deserializer = queryMultiAdapter(
#                         (field, self.context, self.request),
#                         IFieldDeserializer)
#                     if deserializer is None:
#                         continue

#                     try:
#                         value = deserializer(data[name])
#                     except ValueError as e:
#                         errors.append({
#                             'message': e.message, 'field': name, 'error': e})
#                     except ValidationError as e:
#                         errors.append({
#                             'message': e.doc(), 'field': name, 'error': e})
#                     else:
#                         field_data[name] = value
#                         if value != dm.get():
#                             dm.set(value)
#                             modified = True

#                 elif validate_all:
#                     # Never validate the changeNote of p.a.versioningbehavior
#                     # The Versionable adapter always returns an empty string
#                     # which is the wrong type. Should be unicode and should be
#                     # fixed in p.a.versioningbehavior
#                     if name == 'changeNote':
#                         continue
#                     dm = queryMultiAdapter((self.context, field), IDataManager)
#                     bound = field.bind(self.context)
#                     try:
#                         bound.validate(dm.get())
#                     except ValidationError as e:
#                         errors.append({
#                             'message': e.doc(), 'field': name, 'error': e})

#         # Validate schemata
#         for schema, field_data in schema_data.items():
#             validator = queryMultiAdapter(
#                 (self.context, self.request, None, schema, None),
#                 IManagerValidator)
#             for error in validator.validate(field_data):
#                 errors.append({'error': error, 'message': error.message})

#         if errors:
#             raise BadRequest(errors)

#         if modified:
#             notify(ObjectModifiedEvent(self.context))

#         return self.context

#     def check_permission(self, permission_name):
#         if permission_name is None:
#             return True

#         if permission_name not in self.permission_cache:
#             permission = queryUtility(IPermission,
#                                       name=permission_name)
#             if permission is None:
#                 self.permission_cache[permission_name] = True
#             else:
#                 self.permission_cache[permission_name] = bool(
#                     self.sm.checkPermission(permission.title, self.context))
#         return self.permission_cache[permission_name]
