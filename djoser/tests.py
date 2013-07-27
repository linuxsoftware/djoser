from unittest import TestCase
from pprint import pprint
from collections import OrderedDict
from pyramid.testing import DummyRequest, DummyResource
from pagination import CatalogFieldIndexSlicer
from pyramid.testing import setUp, tearDown
from webob.multidict import MultiDict

from .app import AppRoot
from .app import viewRoot
from .contacts import Contacts
from .contacts import viewContacts, viewContact, addContact
from .projects import Projects

class AppRootTests(TestCase):
    def test_AppRoot(self):
        appRoot = AppRoot()
        self.assertEqual(appRoot.__parent__, None)
        self.assertEqual(appRoot.__name__,   None)

class ContactsTests(TestCase):
    def test_Contacts(self):
        appRoot = AppRoot()
        contacts = Contacts(appRoot)
        self.assertEqual(contacts.__parent__, appRoot)
        self.assertEqual(contacts.__name__,   'contacts')

    def test_CatalogIndexSlicer(self):
        #fakeIdx=type('Fake', (object,), {'_fwd_index':{}})()
        fakeIdx = DummyResource(_fwd_index =
                                OrderedDict([("Kami",    [1]),
                                             ("Lorinda", [2,3]),
                                             ("Gonzola", []),
                                             ("Susie",   [4,5,6,7]),
                                             ("Victoria",[8,9])]))
        slicer = CatalogFieldIndexSlicer(fakeIdx, 9)
        self.assertEqual(slicer[0],   1)
        self.assertEqual(slicer[3],   4)
        self.assertEqual(slicer[0:3], [1,2,3])
        self.assertEqual(slicer[:],   range(1,10))
        self.assertEqual(slicer[-2:], [8,9])

class ProjectsTests(TestCase):
    def test_Projects(self):
        appRoot = AppRoot()
        projects = Projects(appRoot)
        self.assertEqual(projects.__parent__, appRoot)
        self.assertEqual(projects.__name__,   'projects')

class ViewTests(TestCase):
    def setUp(self):
        self.config = setUp()

    def tearDown(self):
        tearDown()

    def test_viewRoot(self):
        request = DummyRequest()
        info = viewRoot(request)
        self.assertEqual(info['currentUser'], None)

    #TODO fix up tests to support repoze.catalog
    #def test_viewContacts(self):
    #    context = DummyResource('contacts')
    #    contact = DummyResource(name     = 'Wolfie Smith',
    #                            address1 = '6 Lessingham Ave',
    #                            address2 = 'Tooting',
    #                            city     = 'London',
    #                            postCode = 'SW17 8LU')
    #    context['walter-smith'] = contact
    #    request = DummyRequest()
    #    info = viewContacts(context, request)
    #    pprint(list(info))
    #    row = info['rows'][0]
    #    self.assertEqual(len(row), 9)
    #    #self.assertEqual(row[0], 'walter-smith')
    #    self.assertEqual(row[1], contact.name)
    #    self.assertEqual(row[2], contact.address1)
    #    self.assertEqual(row[3], contact.address2)
    #    self.assertEqual(row[4], contact.city)

    def test_viewContact(self):
        request = DummyRequest()
        contact = DummyResource(name = 'Spike')
        info = viewContact(contact, request)
        self.assertEqual(info['currentUser'], None)

    def test_addContact(self):
        context = DummyResource('contacts',
                                maxKey  = lambda: 1)
        newContact = MultiDict(name     = 'Tucker Clark',
                               address1 = '5/49a Bickley St',
                               address2 = 'Tooting',
                               city     = 'London',
                               postCode = 'SW17 9NF',
                               okBtn    = 'OK')
        request = DummyRequest(post=newContact)
        info = addContact(context, request)
        from pyramid.httpexceptions import HTTPFound
        self.assertIsInstance(info, HTTPFound)
        #self.assertIn('Tucker-Clark', context)


class FunctionalTests(TestCase):
    viewer_login = '/login?login=viewer&password=viewer' \
                   '&came_from=FrontPage&form.submitted=Login'
    viewer_wrong_login = '/login?login=viewer&password=incorrect' \
                   '&came_from=FrontPage&form.submitted=Login'
    editor_login = '/login?login=editor&password=editor' \
                   '&came_from=FrontPage&form.submitted=Login'

    def setUp(self):
        import tempfile
        import os.path
        from . import main
        self.tmpdir = tempfile.mkdtemp()

        dbpath = os.path.join( self.tmpdir, 'test.db')
        uri = 'file://' + dbpath
        settings = { 'zodbconn.uri' : uri ,
                     'pyramid.includes': ['pyramid_zodbconn', 'pyramid_tm'] }

        app = main({}, **settings)
        self.db = app.registry._zodb_databases['']
        from webtest import TestApp
        self.testapp = TestApp(app)

    def tearDown(self):
        import shutil
        self.db.close()
        shutil.rmtree( self.tmpdir )

    def test_Contacts(self):
        res = self.testapp.get( self.viewer_login, status=302)
        res = self.testapp.get('/contacts', status=200)
        self.assertIn('contacts-table', res.body)

    def test_unexisting_page(self):
        res = self.testapp.get('/SomePage', status=404)
        self.assertIn('Not Found', res.body)

    def test_successful_log_in(self):
        res = self.testapp.get( self.viewer_login, status=302)

    def test_failed_log_in(self):
        res = self.testapp.get( self.viewer_wrong_login, status=200)
        self.assertIn('login', res.body)

    def test_logout_link_present_when_logged_in(self):
        res = self.testapp.get( self.viewer_login, status=302)
        res = self.testapp.get('/contacts', status=200)
        self.assertTrue('Logout' in res.body)

    def test_logout_link_not_present_after_logged_out(self):
        res = self.testapp.get( self.viewer_login, status=302)
        res = self.testapp.get('/', status=200)
        res = self.testapp.get('/logout', status=302)
        self.assertTrue('Logout' not in res.body)

