from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.interface import provider

from plone.dexterity.interfaces import IFormFieldProvider


@provider(IFormFieldProvider)
class IDublinCore(IWriteZopeDublinCore):
    pass


from venusianconfiguration import configure
from plone.dexterity.interfaces import IDexterityContent
from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.annotation.interfaces import IAnnotatable
from zope.annotation.interfaces import IAnnotatable


@configure.adapter.factory(for_=(IAnnotatable,), provides=IWriteZopeDublinCore)
class Foo(object):
    def __init__(self, context, request):
        import pdb; pdb.set_trace( )
        self.context = context
        self.request = request
