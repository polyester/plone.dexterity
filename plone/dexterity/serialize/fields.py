# -*- coding: utf-8 -*-
from datetime import timedelta
from plone.dexterity.interfaces import IDexterityContent
from plone.jsonserializer.interfaces import IFieldSerializer
from plone.jsonserializer.serializer.converters import json_compatible
# from plone.namedfile.interfaces import INamedField
# from plone.namedfile.interfaces import INamedFileField
# from plone.namedfile.interfaces import INamedImageField
from plone.registry.interfaces import IRegistry
from plone.restapi.interfaces import IFieldDeserializer
from zope.component import adapter
from zope.component import getMultiAdapter
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
        if not isinstance(value, unicode):
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

