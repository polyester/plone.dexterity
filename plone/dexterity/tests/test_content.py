# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime
from dateutil.tz import gettz
from plone.behavior.interfaces import IBehavior
from plone.behavior.interfaces import IBehaviorAssignable
from plone.behavior.registration import BehaviorRegistration
from plone.dexterity.behavior import DexterityBehaviorAssignable
from plone.dexterity.content import _zone
from plone.dexterity.content import Container
from plone.dexterity.content import Item
from plone.dexterity.fti import DexterityFTI
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.schema import SCHEMA_CACHE
from plone.mocktestcase import MockTestCase
from plone.uuid.adapter import attributeUUID
from plone.uuid.interfaces import IUUID
from zope.annotation.attribute import AttributeAnnotations
from zope.component import provideAdapter
from zope.interface import alsoProvides
from zope.interface import Interface
from zope.traversing.browser.interfaces import IAbsoluteURL

import unittest
import zope.schema


class TestContent(MockTestCase):

    def setUp(self):
        SCHEMA_CACHE.clear()
        provideAdapter(AttributeAnnotations)
        provideAdapter(attributeUUID)

    def test_provided_by_item(self):

        class FauxDataManager(object):
            def setstate(self, obj):
                pass

            def oldstate(self, obj, tid):
                pass

            def register(self, obj):
                pass

        # Dummy instance
        item = Item(id='id')
        item.portal_type = 'testtype'
        item._p_jar = FauxDataManager()

        # Dummy schema
        class ISchema(Interface):
            foo = zope.schema.TextLine(title='foo', default='foo_default')
            bar = zope.schema.TextLine(title='bar')

        class IMarker(Interface):
            pass

        # FTI mock
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.mock_utility(fti_mock, IDexterityFTI, name='testtype')

        self.expect(fti_mock.lookupSchema()).result(ISchema)

        self.replay()

        self.assertFalse(ISchema.implementedBy(Item))

        # Schema as looked up in FTI is now provided by item ...
        self.assertTrue(ISchema.providedBy(item))

        # If the _v_ attribute cache does not work, then we'd expect to have
        # to look up the schema more than once (since we invalidated)
        # the cache. This is not the case, as evidenced by .count(1) above.
        self.assertTrue(ISchema.providedBy(item))

        # We also need to ensure that the _v_ attribute doesn't hide any
        # interface set directly on the instance with alsoProvides() or
        # directlyProvides().  # noqa
        # This is done by clearing the cache when these are invoked.
        alsoProvides(item, IMarker)
        self.assertTrue(IMarker.providedBy(item))
        self.assertTrue(ISchema.providedBy(item))

    def test_provided_by_subclass(self):

        # Make sure the __providedBy__ descriptor lives in sub-classes

        # Dummy type
        class MyItem(Item):
            pass

        class FauxDataManager(object):
            def setstate(self, obj):
                pass

            def oldstate(self, obj, tid):
                pass

            def register(self, obj):
                pass

        # Dummy instance
        item = MyItem(id='id')
        item.portal_type = 'testtype'
        item._p_jar = FauxDataManager()

        # Dummy schema
        class ISchema(Interface):
            foo = zope.schema.TextLine(title='foo', default='foo_default')
            bar = zope.schema.TextLine(title='bar')

        class IMarker(Interface):
            pass

        # FTI mock
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).result(ISchema).count(1)
        self.mock_utility(fti_mock, IDexterityFTI, name='testtype')

        self.replay()

        self.assertFalse(ISchema.implementedBy(MyItem))

        # Schema as looked up in FTI is now provided by item ...
        self.assertTrue(ISchema.providedBy(item))

        # If the _v_ attribute cache does not work, then we'd expect to have
        # to look up the schema more than once (since we invalidated)
        # the cache. This is not the case, as evidenced by .count(1) above.
        self.assertTrue(ISchema.providedBy(item))

        # We also need to ensure that the _v_ attribute doesn't hide any
        # interface set directly on the instance with alsoProvides() or
        # directlyProvides().  # noqa
        # This is done by clearing the cache when these are invoked.
        alsoProvides(item, IMarker)

        self.assertTrue(IMarker.providedBy(item))
        self.assertTrue(ISchema.providedBy(item))

    def test_provided_by_subclass_nojar(self):

        # Dummy type
        class MyItem(Item):
            pass

        # Dummy instance
        item = MyItem(id='id')
        item.portal_type = 'testtype'

        # Without a persistence jar, the _p_changed check doesn't work. In
        # this case, the cache is a bit slower.
        # item._p_jar = FauxDataManager()

        # Dummy schema
        class ISchema(Interface):
            foo = zope.schema.TextLine(title='foo', default='foo_default')
            bar = zope.schema.TextLine(title='bar')

        class IMarker(Interface):
            pass

        # FTI mock
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).result(ISchema).count(1)
        self.mock_utility(fti_mock, IDexterityFTI, name='testtype')

        self.replay()

        self.assertFalse(ISchema.implementedBy(MyItem))

        # Schema as looked up in FTI is now provided by item ...
        self.assertTrue(ISchema.providedBy(item))

        # If the _v_ attribute cache does not work, then we'd expect to have
        # to look up the schema more than once (since we invalidated)
        # the cache. This is not the case, as evidenced by .count(1) above.
        self.assertTrue(ISchema.providedBy(item))

        # We also need to ensure that the _v_ attribute doesn't hide any
        # interface set directly on the instance with alsoProvides() or
        # directlyProvides().  # noqa
        # This is done by clearing the cache when these are invoked.
        alsoProvides(item, IMarker)

        self.assertTrue(IMarker.providedBy(item))
        self.assertTrue(ISchema.providedBy(item))

    def test_provided_by_behavior_subtype(self):

        # Dummy type
        class MyItem(Item):
            pass

        class IMarkerCustom(Interface):
            pass

        # Fake data manager
        class FauxDataManager(object):
            def setstate(self, obj):
                pass

            def oldstate(self, obj, tid):
                pass

            def register(self, obj):
                pass

        # Dummy instance
        item = MyItem(id='id')
        item.portal_type = 'testtype'

        # Without a persistence jar, the _p_changed check doesn't work. In
        # this case, the cache is a bit slower.
        item._p_jar = FauxDataManager()

        # Dummy schema
        class ISchema(Interface):
            foo = zope.schema.TextLine(title='foo', default='foo_default')
            bar = zope.schema.TextLine(title='bar')

        # Schema is not implemented by class or provided by instance
        # XXX :no assert before replay   # noqa
        # self.assertFalse(ISchema.implementedBy(MyItem))
        # self.assertFalse(ISchema.providedBy(item))

        # Behaviors - one with a subtype and one without
        self.mock_adapter(
            DexterityBehaviorAssignable,
            IBehaviorAssignable,
            (IDexterityContent,)
        )

        class IBehavior1(Interface):
            pass

        behavior1 = BehaviorRegistration(
            'Behavior1',
            '',
            IBehavior1,
            None,
            None
        )
        self.mock_utility(behavior1, IBehavior, name='behavior1')

        class IBehavior2(Interface):
            baz = zope.schema.TextLine(title='baz', default='baz')

        class IMarker2(Interface):
            pass

        behavior2 = BehaviorRegistration(
            'Behavior2',
            '',
            IBehavior2,
            IMarker2,
            None
        )
        self.mock_utility(behavior2, IBehavior, name='behavior2')

        # FTI mock
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.mock_utility(fti_mock, IDexterityFTI, name='testtype')

        # expectations
        self.expect(fti_mock.lookupSchema()).result(ISchema)
        self.expect(fti_mock.behaviors).result(['behavior1', 'behavior2'])

        self.replay()

        # start clean
        SCHEMA_CACHE.clear()

        # implementedBy does not look into the fti
        self.assertFalse(ISchema.implementedBy(MyItem))

        # Main schema as looked up in FTI is now provided by item ...
        self.assertTrue(ISchema.providedBy(item))

        # behavior1 does not provide a marker, the schema interface
        # is NOT used as a marker
        self.assertFalse(IBehavior1.providedBy(item))

        # behavior2 provides a marker, so it is used as a marker
        self.assertTrue(IMarker2.providedBy(item))

        # Subtypes provide field defaults.
        self.assertEqual('baz', getattr(item, 'baz', None))

        # We also need to ensure that the _v_ attribute doesn't hide any
        # interface set directly on the instance with alsoProvides() or
        # directlyProvides().  # noqa
        # This is done by clearing the cache when these are invoked.
        alsoProvides(item, IMarkerCustom)
        self.assertTrue(IMarkerCustom.providedBy(item))

        # after directly setting an interface the main-schema and behavior
        # interfaces are still there
        self.assertTrue(ISchema.providedBy(item))
        self.assertFalse(IBehavior1.providedBy(item))
        self.assertTrue(IMarker2.providedBy(item))

    def test_provided_by_behavior_subtype_invalidation(self):

        # Dummy type
        class MyItem(Item):
            pass

        # Fake data manager
        class FauxDataManager(object):
            def setstate(self, obj):
                pass

            def oldstate(self, obj, tid):
                pass

            def register(self, obj):
                pass

        # Dummy instance
        item = MyItem(id='id')
        item.portal_type = 'testtype'

        # Without a persistence jar, the _p_changed check doesn't work. In
        # this case, the cache is a bit slower.
        item._p_jar = FauxDataManager()

        # Dummy schema
        class ISchema(Interface):
            foo = zope.schema.TextLine(title='foo', default='foo_default')
            bar = zope.schema.TextLine(title='bar')

        # Schema is not implemented by class or provided by instance
        # XXX :no assert before replay  # noqa
        # self.assertFalse(ISchema.implementedBy(MyItem))
        # self.assertFalse(ISchema.providedBy(item))

        # Behaviors - one with a marker and one without
        class IBehavior1(Interface):
            pass

        behavior1 = BehaviorRegistration(
            'Behavior1',
            '',
            IBehavior1,
            None,
            None
        )
        self.mock_utility(behavior1, IBehavior, name='behavior1')

        class IBehavior2(Interface):
            pass

        class IMarker2(Interface):
            pass

        behavior2 = BehaviorRegistration(
            'Behavior2',
            '',
            IBehavior2,
            IMarker2,
            None
        )
        self.mock_utility(behavior2, IBehavior, name='behavior2')

        class IBehavior3(Interface):
            pass

        class IMarker3(Interface):
            pass

        behavior3 = BehaviorRegistration(
            'Behavior3',
            '',
            IBehavior3,
            IMarker3,
            None
        )
        self.mock_utility(behavior3, IBehavior, name='behavior3')

        self.mock_adapter(
            DexterityBehaviorAssignable,
            IBehaviorAssignable,
            (IDexterityContent,)
        )

        # FTI mock
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))

        # twice, since we invalidate
        self.expect(fti_mock.lookupSchema()).result(ISchema).count(2)

        # First time around, we have only these behaviors
        self.expect(fti_mock.behaviors).result(
            ['behavior1', 'behavior2']).count(1)

        # Second time around, we add another one
        self.expect(fti_mock.behaviors).result(
            ['behavior1', 'behavior2', 'behavior3']).count(1)

        self.mock_utility(fti_mock, IDexterityFTI, name='testtype')

        self.replay()

        # start clean
        SCHEMA_CACHE.invalidate('testtype')

        # implementedBy does not look into the fti
        self.assertFalse(ISchema.implementedBy(MyItem))

        # Main schema as looked up in FTI is now provided by item ...
        self.assertTrue(ISchema.providedBy(item))

        # Behaviors with its behavior or if provided merker as looked up in
        # FTI is now provided by item ...
        self.assertFalse(IBehavior1.providedBy(item))
        self.assertTrue(IMarker2.providedBy(item))
        self.assertFalse(IMarker3.providedBy(item))

        # If we now invalidate the schema cache, we should get the
        # SECOND set of behaviors (which includes behavior3)
        SCHEMA_CACHE.invalidate('testtype')

        # Main schema as looked up in FTI is now provided by item ...
        self.assertTrue(ISchema.providedBy(item))

        # Behaviors with its behavior or if provided merker as looked up in
        # FTI is now provided by item ...
        self.assertFalse(IBehavior1.providedBy(item))
        self.assertTrue(IMarker2.providedBy(item))
        self.assertTrue(IMarker3.providedBy(item))

        # If the _v_ attribute cache does not work, then we'd expect to have
        # to look up the schema more than once (since we invalidated)
        # the cache. This is not the case, as evidenced by .count(1) above.
        self.assertTrue(ISchema.providedBy(item))
        self.assertFalse(IBehavior1.providedBy(item))
        self.assertTrue(IMarker2.providedBy(item))
        self.assertTrue(IMarker3.providedBy(item))

    def test_getattr_consults_schema_item(self):

        content = Item()
        content.id = 'id'
        content.portal_type = 'testtype'

        class ISchema(Interface):
            foo = zope.schema.TextLine(title='foo', default='foo_default')
            bar = zope.schema.TextLine(title='bar')

        # FTI mock
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).result(ISchema)
        self.mock_utility(fti_mock, IDexterityFTI, name='testtype')

        self.replay()

        SCHEMA_CACHE.invalidate('testtype')

        self.assertEqual('foo_default', content.foo)
        self.assertEqual(None, content.bar)
        self.assertEqual('id', content.id)
        self.assertRaises(AttributeError, getattr, content, 'baz')

    def test_getattr_consults_schema_container(self):

        content = Container()
        content.id = 'id'
        content.portal_type = 'testtype'

        class ISchema(Interface):
            foo = zope.schema.TextLine(title='foo', default='foo_default')
            bar = zope.schema.TextLine(title='bar')

        # FTI mock
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).result(ISchema)
        self.mock_utility(fti_mock, IDexterityFTI, name='testtype')

        self.replay()

        SCHEMA_CACHE.invalidate('testtype')

        self.assertEqual('foo_default', content.foo)
        self.assertEqual(None, content.bar)
        self.assertEqual('id', content.id)
        self.assertRaises(AttributeError, getattr, content, 'baz')

    def test_getattr_consults_schema_item_default_factory_with_context(self):

        content = Item()
        content.id = 'id'
        content.portal_type = 'testtype'

        from zope.interface import provider
        from zope.schema.interfaces import IContextAwareDefaultFactory

        @provider(IContextAwareDefaultFactory)
        def defaultFactory(context):
            return '{0:s}_{1:s}'.format(context.id, context.portal_type)

        class ISchema(Interface):
            foo = zope.schema.TextLine(title='foo',
                                       defaultFactory=defaultFactory)
            bar = zope.schema.TextLine(title='bar')

        # FTI mock
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).result(ISchema)
        self.mock_utility(fti_mock, IDexterityFTI, name='testtype')

        self.replay()

        SCHEMA_CACHE.invalidate('testtype')

        self.assertEqual('id_testtype', content.foo)
        self.assertEqual(None, content.bar)
        self.assertEqual('id', content.id)
        self.assertRaises(AttributeError, getattr, content, 'baz')

    def test_getattr_on_container_returns_children(self):

        content = Container()
        content.id = 'id'
        content.portal_type = 'testtype'

        content['foo'] = Item('foo')
        content['quux'] = Item('quux')

        class ISchema(Interface):
            foo = zope.schema.TextLine(title='foo', default='foo_default')
            bar = zope.schema.TextLine(title='bar')

        # FTI mock
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).result(ISchema)
        self.mock_utility(fti_mock, IDexterityFTI, name='testtype')

        self.replay()

        SCHEMA_CACHE.invalidate('testtype')

        # Schema field masks contained item
        self.assertEqual('foo_default', content.foo)

        # But we can still obtain an item
        self.assertTrue(isinstance(content['foo'], Item))
        self.assertEqual('foo', content['foo'].id)

        # And if the item isn't masked by an attribute, we can still getattr it
        self.assertTrue(isinstance(content['quux'], Item))
        self.assertEqual('quux', content['quux'].id)

        self.assertTrue(isinstance(getattr(content, 'quux'), Item))
        self.assertEqual('quux', getattr(content, 'quux').id)

    def test_name_and_id_in_sync(self):

        i = Item()
        self.assertEqual('', i.id)
        self.assertEqual('', i.getId())
        self.assertEqual('', i.__name__)

        i = Item()
        i.id = 'foo'
        self.assertEqual('foo', i.id)
        self.assertEqual('foo', i.getId())
        self.assertEqual('foo', i.__name__)

        i = Item()
        i.__name__ = 'foo'
        self.assertEqual('foo', i.id)
        self.assertEqual('foo', i.getId())
        self.assertEqual('foo', i.__name__)

    def test_name_unicode_id_str(self):

        i = Item()

        try:
            i.__name__ = '\xc3\xb8'.decode('utf-8')
        except UnicodeEncodeError:
            pass
        else:
            self.fail()

        i.__name__ = 'o'

        self.assertEqual('o', i.__name__)
        self.assertEqual('o', i.id)
        self.assertEqual('o', i.getId())

        self.assertTrue(isinstance(i.__name__, str))
        self.assertTrue(isinstance(i.id, str))
        self.assertTrue(isinstance(i.getId(), str))

    def test_item_dublincore(self):
        i = Item(
            title='Emperor Penguin',
            description='One of the most magnificent birds.',
            subject='Penguins',
            contributors='admin',
            effective_date=datetime(2010, 8, 20, tzinfo=_zone),
            expiration_date=datetime(2013, 7, 9, tzinfo=_zone),
            format='text/plain',
            language='de',
            rights='CC',
        )

        summer_timezone = i.effective_date.tzinfo
        self.assertEqual(i.title, 'Emperor Penguin')
        self.assertEqual(i.Title(), 'Emperor Penguin')
        self.assertEqual(i.description, 'One of the most magnificent birds.')
        self.assertEqual(i.Description(), 'One of the most magnificent birds.')
        self.assertEqual(i.subject, ('Penguins',))
        self.assertEqual(i.Subject(), ('Penguins',))
        self.assertEqual(i.contributors, ('admin',))
        self.assertEqual(i.listContributors(), ('admin',))
        self.assertEqual(i.Contributors(), ('admin',))
        self.assertEqual(i.format, 'text/plain')
        self.assertEqual(i.effective_date, datetime(2010, 8, 20, tzinfo=_zone))
        self.assertEqual(
            i.EffectiveDate(zone=summer_timezone)[:10], '2010-08-20')
        self.assertEqual(i.effective(), datetime(2010, 8, 20, tzinfo=_zone))
        self.assertEqual(i.expiration_date, datetime(2013, 7, 9, tzinfo=_zone))
        self.assertEqual(
            i.ExpirationDate(zone=summer_timezone)[:10], '2013-07-09')
        self.assertEqual(i.expires(), datetime(2013, 7, 9, tzinfo=_zone))
        self.assertEqual(i.language, 'de')
        self.assertEqual(i.Language(), 'de')  # noqa
        self.assertEqual(i.rights, 'CC')
        self.assertEqual(i.Rights(), 'CC')
        self.assertEqual(i.creation_date, i.created())
        self.assertEqual(
            i.CreationDate(zone=summer_timezone)[:19],
            i.creation_date.isoformat()[:19]
        )
        self.assertEqual(i.modification_date, i.creation_date)
        self.assertEqual(i.modification_date, i.modified())
        self.assertEqual(
            i.ModificationDate(zone=summer_timezone)[:19],
            i.modification_date.isoformat()[:19]
        )
        self.assertEqual(i.Date(), i.EffectiveDate())
        self.assertEqual(
            i.Identifier(),
            str(IAbsoluteURL(i, IUUID(i))))  # noqa

    def test_item_dublincore_date(self):
        # Mock Zope DateTime
        import mock
        import plone.dexterity
        datetime_patcher = mock.patch.object(
            plone.dexterity.content, 'datetime'
        )
        mocked_datetime = datetime_patcher.start()
        mocked_datetime.return_value = datetime(2014, 6, 1, tzinfo=_zone)
        self.addCleanup(datetime_patcher.stop)

        i = Item(
            title='Emperor Penguin',
            description='One of the most magnificent birds.',
            subject='Penguins',
            contributors='admin',
            effective_date=date(2010, 8, 20, tzinfo=_zone),
            expiration_date=date(2013, 7, 9, tzinfo=_zone),
            format='text/plain',
            language='de',
            rights='CC',
        )

        summer_timezone = datetime(2010, 8, 20, tzinfo=_zone).tzinfo
        self.assertEqual(i.effective_date, datetime(2010, 8, 20, tzinfo=_zone))
        self.assertEqual(
            i.EffectiveDate(zone=summer_timezone)[:10], '2010-08-20')
        self.assertEqual(i.effective(), datetime(2010, 8, 20, tzinfo=_zone))
        self.assertEqual(
            i.expiration_date, datetime(20130, 7, 9, tzinfo=_zone))
        self.assertEqual(
            i.ExpirationDate(zone=summer_timezone)[:10], '2013-07-09')
        self.assertEqual(i.expires(), datetime(2013, 7, 9, tzinfo=_zone))
        self.assertEqual(i.creation_date, i.created())
        self.assertEqual(
            i.CreationDate(zone=summer_timezone)[:19],
            i.creation_date.ISO()[:19]
        )
        self.assertEqual(i.modification_date, i.creation_date)
        self.assertEqual(i.modification_date, i.modified())
        self.assertEqual(
            i.ModificationDate(zone=summer_timezone)[:19],
            i.modification_date.ISO()[:19]
        )
        self.assertEqual(i.Date(), i.EffectiveDate())

    def test_item_dublincore_datetime(self):
        i = Item(
            title='Emperor Penguin',
            description='One of the most magnificent birds.',
            subject='Penguins',
            contributors='admin',
            effective_date=datetime(
                2010, 8, 20, 12, 59, 59, 0, tzinfo=gettz('US/Eastern')),
            expiration_date=datetime(
                2013, 7, 9, 12, 59, 59, 0, tzinfo=gettz('US/Eastern')),
            format='text/plain',
            language='de',
            rights='CC',
        )

        summer_timezone = datetime(2010, 8, 20, tzinfo=_zone)
        self.assertEqual(
            i.effective_date,
            datetime(2010, 8, 20, 12, 59, 59, tzinfo=gettz('US/Eastern'))
        )
        self.assertEqual(
            i.EffectiveDate(zone=summer_timezone),
            datetime(2010, 8, 20, 12, 59, 59, tzinfo=gettz('US/Eastern'))
            .astimezone(summer_timezone).isoformat()
        )
        self.assertEqual(
            i.effective(),
            datetime(2010, 8, 20, 12, 59, 59, tzinfo=gettz('US/Eastern'))
        )
        self.assertEqual(
            i.expiration_date,
            datetime(2013, 7, 9, 12, 59, 59, tzinfo=gettz('US/Eastern'))
        )
        self.assertEqual(
            i.ExpirationDate(zone=summer_timezone),
            datetime(2013, 7, 9, 12, 59, 59, tzinfo=gettz('US/Eastern'))
            .astimezone(summer_timezone).isoformat()
        )
        self.assertEqual(
            i.expires(),
            datetime(2013, 7, 9, 12, 59, 59, tzinfo=gettz('US/Eastern'))
        )
        self.assertEqual(i.creation_date, i.created())
        self.assertEqual(
            i.CreationDate(zone=summer_timezone),
            i.creation_date.isoformat()
        )
        self.assertEqual(i.modification_date, i.creation_date)
        self.assertEqual(i.modification_date, i.modified())
        self.assertEqual(
            i.ModificationDate(zone=summer_timezone),
            i.modification_date.isoformat()
        )
        self.assertEqual(i.Date(), i.EffectiveDate())

    def test_item_notifyModified(self):
        i = Item()

        def mock_addCreator():
            mock_addCreator.called = True
        i.addCreator = mock_addCreator

        i.setModificationDate(datetime.min)

        i.notifyModified()
        self.assertNotEqual(i.modification_date, i.creation_date)
        self.assertNotEqual(i.modification_date, datetime.min)
        self.assertTrue(mock_addCreator.called)

    def test_item_addCreator(self):
        i = Item()
        i.addCreator('harvey')
        self.assertEqual(i.creators, ('harvey',))
        self.assertEqual(i.listCreators(), ('harvey',))
        self.assertEqual(i.Creator(), 'harvey')

    def test_item_Type(self):
        i = Item()

        def mock_getTypeInfo():
            class TypeInfo(object):
                def Title(self):
                    return 'Foo'
            return TypeInfo()
        i.getTypeInfo = mock_getTypeInfo

        self.assertEqual(i.Type(), 'Foo')

    def test_item_init_nondc_kwargs(self):
        i = Item(foo='bar')
        self.assertEqual(i.foo, 'bar')

    def test_container_init_dublincore(self):
        c = Container(
            title='Test title',
            language='en',
            effective_date=datetime(2010, 8, 20)
        )
        self.assertEqual(c.title, 'Test title')
        self.assertEqual(c.language, 'en')
        self.assertTrue(isinstance(c.effective_date, datetime))

    def test_container_init_nondc_kwargs(self):
        c = Container(foo='bar')
        self.assertEqual(c.foo, 'bar')

    def test_setTitle_converts_to_str(self):
        # fix http://code.google.com/p/dexterity/issues/detail?id=145
        i = Item()
        i.setTitle('é')
        self.assertEqual(i.title, 'é')
        i.setTitle('é')
        self.assertEqual(i.title, 'é')
        c = Container()
        c.setTitle('é')
        self.assertEqual(c.title, 'é')
        c.setTitle('é')
        self.assertEqual(c.title, 'é')

    def test_Title_converts_to_utf8(self):
        i = Item()
        i.title = 'é'
        self.assertEqual('é', i.Title())
        i.title = 'é'
        self.assertEqual('é', i.Title())
        c = Container()
        c.title = 'é'
        self.assertEqual('é', c.Title())
        c.title = 'é'
        self.assertEqual('é', c.Title())

    def test_Title_handles_None(self):
        i = Item(title=None)
        self.assertEqual('', i.Title())
        c = Container(title=None)
        self.assertEqual('', c.Title())

    def test_Creator_returns_str(self):  # was _converts_to_utf8
        i = Item()
        i.creators = ('é',)
        self.assertEqual('é', i.Creator())
        i.creators = ('é',)
        self.assertEqual('é', i.Creator())
        c = Container()
        c.creators = ('é',)
        self.assertEqual('é', c.Creator())
        self.assertEqual(('é',), c.creators)

    def test_Creator_handles_None(self):
        i = Item(creators=None)
        self.assertEqual('', i.Creator())
        c = Container(creators=None)
        self.assertEqual('', c.Creator())

    def test_Description_returns_str(self):
        i = Item()
        i.description = 'é'
        self.assertEqual('é', i.Description())
        i.description = 'é'
        self.assertEqual('é', i.Description())
        c = Container()
        c.description = 'é'
        self.assertEqual('é', c.Description())
        c.description = 'é'
        self.assertEqual('é', c.Description())

    def test_setDescription_converts_to_str(self):
        i = Item()
        i.setDescription('é')
        self.assertEqual(i.description, 'é')
        i.setDescription('é')
        self.assertEqual(i.description, 'é')
        c = Container()
        c.setDescription('é')
        self.assertEqual(c.description, 'é')
        c.setDescription('é')
        self.assertEqual(c.description, 'é')

    def test_Description_handles_None(self):
        i = Item(description=None)
        self.assertEqual('', i.Description())
        c = Container(description=None)
        self.assertEqual('', c.Description())

    def test_Subject_converts_to_utf8(self):
        i = Item()
        i.subject = ('é',)
        self.assertEqual(('é',), i.Subject())
        i.subject = ('é',)
        self.assertEqual(('é',), i.Subject())
        c = Container()
        c.subject = ('é',)
        self.assertEqual(('é',), c.Subject())
        c.subject = ('é',)
        self.assertEqual(('é',), c.Subject())

    def test_setSubject_converts_to_str(self):
        i = Item()
        i.setSubject(('é',))
        self.assertEqual(i.subject, ('é',))
        i.setSubject(('é',))
        self.assertEqual(i.subject, ('é',))
        c = Container()
        c.setSubject(('é',))
        self.assertEqual(c.subject, ('é',))
        c.setSubject(('é',))
        self.assertEqual(c.subject, ('é',))

    def test_Subject_handles_None(self):
        i = Item()
        i.subject = None
        self.assertEqual((), i.Subject())
        c = Container()
        c.subject = None
        self.assertEqual((), c.Subject())

    def test_field_default_independence(self):
        # Ensure that fields using the default value aren't being assigned
        # shallow copies.

        class FauxDataManager(object):
            def setstate(self, obj):
                pass

            def oldstate(self, obj, tid):
                pass

            def register(self, obj):
                pass

        # Dummy instances
        foo = Item(id='foo')
        foo.portal_type = 'testtype'
        foo._p_jar = FauxDataManager()

        bar = Item(id='bar')
        bar.portal_type = 'testtype'
        bar._p_jar = FauxDataManager()

        baz = Container(id='baz')
        baz.portal_type = 'testtype'
        baz._p_jar = FauxDataManager()

        # Dummy schema
        class ISchema(Interface):
            listfield = zope.schema.List(title='listfield', default=[1, 2])

        # FTI mock
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).result(ISchema).count(1)
        self.mock_utility(fti_mock, IDexterityFTI, name='testtype')

        self.replay()

        # Ensure that the field of foo is not the same field, also attached to
        # bar.
        self.assertTrue(foo.listfield is not bar.listfield)
        self.assertTrue(foo.listfield is not baz.listfield)
        # And just to reinforce why this is awful, we'll ensure that updating
        # the field's value on one object does not change the value on the
        # other.
        foo.listfield.append(3)
        self.assertEqual(bar.listfield, [1, 2])
        self.assertEqual(baz.listfield, [1, 2])


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
