# -*- coding: utf-8 -*-
from plone.dexterity.interfaces import IDexterityContent
from plone.namedfile.interfaces import INamedFileField
from plone.namedfile.interfaces import INamedImageField
from plone.registry.interfaces import IRegistry
from plone.restapi.interfaces import IFieldSerializer
from plone.restapi.serializer.converters import json_compatible
from zope.component import adapter
from zope.component import getUtility
from zope.interface import implementer
from zope.interface import Interface
from zope.schema.interfaces import IField


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


@adapter(INamedImageField, IDexterityContent, Interface)
class ImageFieldSerializer(DefaultFieldSerializer):

    def __call__(self):
        absolute_url = self.context.absolute_url()
        urls = {name: '{0}/@@images/image/{1}'.format(absolute_url, name)
                for name in self.get_scale_names()}
        urls['original'] = '/'.join((self.context.absolute_url(),
                                     '@@images',
                                     self.field.__name__))
        return json_compatible(urls)

    def get_scale_names(self):
        registry = getUtility(IRegistry)
        # TODO: Get scale names from somewhere.
        # from Products.CMFPlone.interfaces import IImagingSchema
        # imaging_settings = registry.forInterface(
        #     IImagingSchema,
        #     prefix='plone'
        # )
        # allowed_sizes = imaging_settings.allowed_sizes

        # return [size.split(' ')[0] for size in allowed_sizes]


@adapter(INamedFileField, IDexterityContent, Interface)
class FileFieldSerializer(DefaultFieldSerializer):

    def __call__(self):
        url = '/'.join((self.context.absolute_url(),
                        '@@download',
                        self.field.__name__))
        return json_compatible(url)
