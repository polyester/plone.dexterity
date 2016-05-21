# -*- coding: utf-8 -*-
# from plone.namedfile.interfaces import INamedField
# from plone.namedfile.interfaces import INamedFileField
# from plone.namedfile.interfaces import INamedImageField
from datetime import timedelta
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.interfaces import IDexterityFTI
from plone.jsonserializer.interfaces import IFieldDeserializer
from plone.jsonserializer.interfaces import IFieldSerializer
from plone.jsonserializer.interfaces import IFieldsetSerializer
from plone.jsonserializer.interfaces import ISchemaSerializer
from plone.jsonserializer.serializer.converters import json_compatible
from plone.registry.interfaces import IRegistry
from plone.supermodel.interfaces import IFieldset
from plone.supermodel.interfaces import IFieldNameExtractor
from plone.supermodel.interfaces import ISchema
from plone.supermodel.interfaces import IToUnicode
from plone.supermodel.model import Schema
from plone.supermodel.utils import sortedFields
from zope.component import adapter
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.i18nmessageid import Message
from zope.interface import implementedBy
from zope.interface import implementer
from zope.interface import Interface
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.schema.interfaces import ICollection
from zope.schema.interfaces import IDatetime
from zope.schema.interfaces import IDict
from zope.schema.interfaces import IField
from zope.schema.interfaces import IFromUnicode
from zope.schema.interfaces import ITime
from zope.schema.interfaces import ITimedelta
import zope.schema


@adapter(IField, IDexterityContent, Interface)
@implementer(IFieldSerializer)
class DefaultFieldSerializer(object):

    def __init__(self, field, context, request):
        self.context = context
        self.request = request
        self.field = field

    def __call__(self):
        return json_compatible(self.get_value())

    def get_value(self, default=None):
        return getattr(self.field.interface(self.context),
                       self.field.__name__,
                       default)


@adapter(ISchema, IDexterityFTI, Interface)
@implementer(ISchemaSerializer)
class DefaultSchemaSerializer(object):

    def __init__(self, schema, fti, request):
        self.schema = schema
        self.fti = fti
        self.request = request

    def __call__(self):
        result = {'based_on': self.bases,
                  'invariants': self.invariants,
                  'fields': self.field_ids}

        return result

    @property
    def name(self):
        return self.schema.__name__

    @property
    def field_ids(self):
        return [n for n, s in sortedFields(self.schema)]

    @property
    def bases(self):
        return [b.__identifier__ for b in self.schema.__bases__
                if b is not Schema]

    @property
    def invariants(self):
        return ''


@adapter(IFieldset, ISchema, IDexterityFTI, Interface)
@implementer(IFieldsetSerializer)
class DefaultFieldsetSerializer(object):

    def __init__(self, fieldset, schema, fti, request):
        self.fieldset = fieldset
        self.schema = schema
        self.fti = fti
        self.request = request

    def __call__(self):
        result = {'label': self.label,
                  'properties': {}
                  }

        result['properties'] = self.fields
        return result

    @property
    def name(self):
        return self.fieldset.__name__

    @property
    def label(self):
        return self.fieldset.label

    @property
    def fields(self):
        result = {}
        for field_name in self.fieldset.fields:
            field = self.schema[field_name]
            serializer = getMultiAdapter((field, self.schema, self.fti, self.request), IFieldSerializer)
            result[field_name] = serializer()
        return result


@adapter(IField, ISchema, IDexterityFTI, Interface)
@implementer(IFieldSerializer)
class DefaultFTIFieldSerializer(object):

    # Elements we won't write
    filtered_attributes = ['order', 'unique', 'defaultFactory']

    # Elements that are of the same type as the field itself
    field_type_attributes = ('min', 'max', 'default', )

    # Elements that are of the same type as the field itself, but are
    # otherwise not validated
    non_validated_field_type_attributes = ('missing_value', )

    # Attributes that contain another field. Unfortunately,
    field_instance_attributes = ('key_type', 'value_type', )

    # Fields that are always written
    forced_fields = frozenset(['default', 'missing_value'])

    def __init__(self, field, schema, fti, request):
        self.field = field
        self.schema = schema
        self.fti = fti
        self.request = request
        self.klass = fti.klass
        self.field_attributes = {}

        # Build a dict of the parameters supported by this field type.
        # Each parameter is itself a field, which can be used to convert
        # text input to an appropriate object.
        for schema in implementedBy(self.field.__class__).flattened():
            self.field_attributes.update(zope.schema.getFields(schema))

        self.field_attributes['defaultFactory'] = zope.schema.Object(
            __name__='defaultFactory',
            title=u"defaultFactory",
            schema=Interface
        )

    def __call__(self):
        schema = {'type': self.field_type}
        for attribute_name in sorted(self.field_attributes.keys()):
            attribute_field = self.field_attributes[attribute_name]
            if attribute_name in self.filtered_attributes:
                continue

            element_name = attribute_field.__name__
            attribute_field = attribute_field.bind(self.field)
            force = (element_name in self.forced_fields)
            value = attribute_field.get(self.field)

            # if ignoreDefault and value == attributeField.default:
            #     return None

            # # The value points to another field. Recurse.
            # if IField.providedBy(value):
            #     value_fieldType = IFieldNameExtractor(value)()
            #     handler = queryUtility(
            #         IFieldExportImportHandler,
            #         name=value_fieldType
            #     )
            #     if handler is None:
            #         return None
            #     return handler.write(
            #         value, name=None,
            #         type=value_fieldType,
            #         elementName=elementName
            #     )

            # For 'default', 'missing_value' etc, we want to validate against
            # the imported field type itself, not the field type of the attribute
            if element_name in self.field_type_attributes or \
                    element_name in self.non_validated_field_type_attributes:
                attribute_field = self.field

            if isinstance(value, bytes) and not isinstance(value, str):
                value = value.decode('utf-8')

            if value is not None and (force or value != self.field.missing_value):
                converter = IToUnicode(self.field)
                text = converter.toUnicode(value)

                # handle i18n
                # if isinstance(value, Message):
                #     child.set(ns('domain', I18N_NAMESPACE), value.domain)
                #     if not value.default:
                #         child.set(ns('translate', I18N_NAMESPACE), '')
                #     else:
                #         child.set(ns('translate', I18N_NAMESPACE), child.text)
                #         child.text = converter.toUnicode(value.default)
                schema[attribute_name] = text

        return schema

    @property
    def field_type(self):
        name_extractor = IFieldNameExtractor(self.field)
        return name_extractor()



# TODO: Move to plone.namedfield
# @adapter(INamedImageField, IDexterityContent, Interface)
# class ImageFieldSerializer(DefaultFieldSerializer):

#     def __call__(self):
#         absolute_url = self.context.absolute_url()
#         urls = {name: '{0}/@@images/image/{1}'.format(absolute_url, name)
#                 for name in self.get_scale_names()}
#         urls['original'] = '/'.join((self.context.absolute_url(),
#                                      '@@images',
#                                      self.field.__name__))
#         return json_compatible(urls)

#     def get_scale_names(self):
#         registry = getUtility(IRegistry)
#         # TODO: Get scale names from somewhere.
#         # from Products.CMFPlone.interfaces import IImagingSchema
#         # imaging_settings = registry.forInterface(
#         #     IImagingSchema,
#         #     prefix='plone'
#         # )
#         # allowed_sizes = imaging_settings.allowed_sizes

#         # return [size.split(' ')[0] for size in allowed_sizes]


# @adapter(INamedFileField, IDexterityContent, Interface)
# class FileFieldSerializer(DefaultFieldSerializer):

#     def __call__(self):
#         url = '/'.join((self.context.absolute_url(),
#                         '@@download',
#                         self.field.__name__))
#         return json_compatible(url)


@implementer(IFieldDeserializer)
@adapter(IField, IDexterityContent, IBrowserRequest)
class DefaultFieldDeserializer(object):

    def __init__(self, field, context, request):
        self.field = field
        self.context = context
        self.request = request

    def __call__(self, value):
        if not isinstance(value, str):
            return value
        return IFromUnicode(self.field).fromUnicode(value)


@implementer(IFieldDeserializer)
@adapter(IDatetime, IDexterityContent, IBrowserRequest)
class DatetimeFieldDeserializer(DefaultFieldDeserializer):

    def __call__(self, value):
        try:
            # Parse ISO 8601 string with Zope's DateTime module
            # and convert to a timezone naive datetime in local time
            value = DateTime(value).toZone(DateTime().localZone()).asdatetime(
            ).replace(tzinfo=None)
        except (SyntaxError, DateTimeError) as e:
            raise ValueError(e.message)

        self.field.validate(value)
        return value


@implementer(IFieldDeserializer)
@adapter(ICollection, IDexterityContent, IBrowserRequest)
class CollectionFieldDeserializer(DefaultFieldDeserializer):

    def __call__(self, value):
        if not isinstance(value, list):
            value = [value]

        if IField.providedBy(self.field.value_type):
            deserializer = getMultiAdapter(
                (self.field.value_type, self.context, self.request),
                IFieldDeserializer)

            for i, v in enumerate(value):
                value[i] = deserializer(v)

        value = self.field._type(value)
        self.field.validate(value)

        return value


@implementer(IFieldDeserializer)
@adapter(IDict, IDexterityContent, IBrowserRequest)
class DictFieldDeserializer(DefaultFieldDeserializer):

    def __call__(self, value):
        kdeserializer = lambda k: k
        vdeserializer = lambda v: v
        if IField.providedBy(self.field.key_type):
            kdeserializer = getMultiAdapter(
                (self.field.key_type, self.context, self.request),
                IFieldDeserializer)
        if IField.providedBy(self.field.value_type):
            vdeserializer = getMultiAdapter(
                (self.field.value_type, self.context, self.request),
                IFieldDeserializer)

        new_value = {}
        for k, v in value.items():
            new_value[kdeserializer(k)] = vdeserializer(v)

        self.field.validate(new_value)
        return new_value


@implementer(IFieldDeserializer)
@adapter(ITime, IDexterityContent, IBrowserRequest)
class TimeFieldDeserializer(DefaultFieldDeserializer):

    def __call__(self, value):
        try:
            # Create an ISO 8601 datetime string and parse it with Zope's
            # DateTime module and then convert it to a timezone naive time
            # in local time
            value = DateTime(u'2000-01-01T' + value).toZone(DateTime(
            ).localZone()).asdatetime().replace(tzinfo=None).time()
        except (SyntaxError, DateTimeError):
            raise ValueError(u'Invalid time: {}'.format(value))

        self.field.validate(value)
        return value


@implementer(IFieldDeserializer)
@adapter(ITimedelta, IDexterityContent, IBrowserRequest)
class TimedeltaFieldDeserializer(DefaultFieldDeserializer):

    def __call__(self, value):
        try:
            value = timedelta(seconds=value)
        except TypeError as e:
            raise ValueError(e.message)

        self.field.validate(value)
        return value

# TODO: Move to named field
# @implementer(IFieldDeserializer)
# @adapter(INamedField, IDexterityContent, IBrowserRequest)
# class NamedFieldDeserializer(DefaultFieldDeserializer):

#     def __call__(self, value):
#         content_type = 'application/octet-stream'
#         filename = None
#         if isinstance(value, dict):
#             content_type = value.get(u'content-type', content_type).encode(
#                 'utf8')
#             filename = value.get(u'filename', filename)
#             if u'encoding' in value:
#                 data = value.get('data', '').decode(value[u'encoding'])
#             else:
#                 data = value.get('data', '')
#         else:
#             data = value

#         value = self.field._type(
#             data=data, contentType=content_type, filename=filename)
#         self.field.validate(value)
#         return value

