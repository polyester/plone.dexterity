from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.interface import provider
from zope.interface import implementer
from zope.component import adapter
from plone.dexterity.interfaces import IFormFieldProvider


@provider(IFormFieldProvider)
class IDublinCore(IWriteZopeDublinCore):
    pass


from plone.dexterity.interfaces import IDexterityContent
from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.annotation.interfaces import IAnnotatable


@adapter(IAnnotatable)
@implements(IWriteZopeDublinCore)
class Foo(object):
    def __init__(self, context, request):
        import pdb; pdb.set_trace( )
        self.context = context
        self.request = request
