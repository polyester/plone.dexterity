# from plone.autoform.interfaces import READ_PERMISSIONS_KEY
from plone.dexterity.interfaces import IDexterityContainer
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.utils import iterSchemata
from plone.jsonserializer.interfaces import IFieldSerializer
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.jsonserializer.interfaces import ISerializeToJsonSummary
from plone.jsonserializer.serializer.converters import json_compatible
from plone.supermodel.utils import mergedTaggedValueDict
from zope.component import adapter
from zope.component import ComponentLookupError
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.interface import Interface
from zope.interface import implementer
from zope.schema import getFields
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
        try:
            parent_summary = getMultiAdapter(
                (parent, self.request), ISerializeToJsonSummary)()
        except ComponentLookupError:
            parent_summary = {}
        result = {
            # '@context': 'http://www.w3.org/ns/hydra/context.jsonld',
            '@id': '',  # TODO: self.context.absolute_url(),
            '@type': self.context.portal_type,
            'parent': parent_summary,
            'created': json_compatible(self.context.created),
            'modified': json_compatible(self.context.modified),
            'UID': self.context.UID(),
        }

        import pdb; pdb.set_trace( )
        for schema in iterSchemata(self.context):

            read_permissions = []
            # TODO: read_permissions = mergedTaggedValueDict(schema, READ_PERMISSIONS_KEY)

            for name, field in getFields(schema).items():

                # TODO: if not self.check_permission(read_permissions.get(name)):
                #     continue

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
                sm = getSecurityManager()
                self.permission_cache[permission_name] = bool(
                    sm.checkPermission(permission.title, self.context))
        return self.permission_cache[permission_name]


@implementer(ISerializeToJson)
@adapter(IDexterityContainer, Interface)
class SerializeFolderToJson(SerializeToJson):

    def __call__(self):
        result = super(SerializeFolderToJson, self).__call__()
        result['member'] = [
            getMultiAdapter((member, self.request), ISerializeToJsonSummary)()
            for member in self.context.objectValues()
        ]
        return result
