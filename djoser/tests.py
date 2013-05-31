from unittest import TestCase
from pprint import pprint
from pyramid.testing import DummyRequest, DummyResource
from pyramid.testing import setUp, tearDown
from webob.multidict import MultiDict


class AppRootTests(TestCase):
    def test_AppRoot(self):
        from .models import AppRoot
        appRoot = AppRoot()
        self.assertEqual(appRoot.__parent__, None)
        self.assertEqual(appRoot.__name__,   None)

class ContactsTests(TestCase):
    def test_Contacts(self):
        from .models import AppRoot, Contacts
        appRoot = AppRoot()
        contacts = Contacts(appRoot)
        self.assertEqual(contacts.__parent__, appRoot)
        self.assertEqual(contacts.__name__,   'contacts')

class ProjectsTests(TestCase):
    def test_Projects(self):
        from .models import AppRoot, Projects
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
        from .views import viewRoot
        request = DummyRequest()
        info = viewRoot(request)
        self.assertEqual(info['project'], 'd3')

    def test_viewContacts(self):
        from .views import viewContacts
        context = DummyResource('contacts')
        contact = DummyResource(name     = 'Wolfie Smith',
                                address1 = '6 Lessingham Ave',
                                address2 = 'Tooting',
                                city     = 'London',
                                postCode = 'SW17 8LU')
        context['walter-smith'] = contact
        request = DummyRequest()
        info = viewContacts(context, request)
        row = info['rows'][0]
        self.assertEqual(len(row), 9)
        self.assertEqual(row[0], 'walter-smith')
        self.assertEqual(row[1], contact.name)
        self.assertEqual(row[2], contact.address1)
        self.assertEqual(row[3], contact.address2)
        self.assertEqual(row[4], contact.city)

    def test_viewContact(self):
        from .views import viewContact
        request = DummyRequest()
        info = viewContact(request)
        self.assertEqual(info['project'], 'd3')

    def test_addContact(self):
        from .views import addContact
        context = DummyResource('contacts')
        newContact = MultiDict(name     = 'Tucker Clark',
                               address1 = '5/49a Bickley St',
                               address2 = 'Tooting',
                               city     = 'London',
                               postCode = 'SW17 9NF',
                               OK       = 'OK')
        request = DummyRequest(post=newContact)
        info = addContact(context, request)
        from pyramid.httpexceptions import HTTPFound
        self.assertIsInstance(info, HTTPFound)
        self.assertIn('Tucker-Clark', context)


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

