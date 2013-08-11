# ------------------------------------------------------------------------------
# Contact Resources
# ------------------------------------------------------------------------------
from persistent import Persistent
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import ALL_PERMISSIONS
from pyramid.security import DENY_ALL
import transaction

from .table import Table

class Contacts(Table):
    __acl__    = [(Allow, Authenticated,   'view'),
                  (Allow, 'group:editor',  ['view', 'edit']),
                  (Allow, 'group:admin',   ALL_PERMISSIONS),
                  DENY_ALL]
    __name__   = 'contacts'
    Headings   = ['name', 'address1', 'address2', 'city',
                  'postCode', 'country', 'phone', 'email']

    def __init__(self, parent):
        Table.__init__(self, parent, Contacts.Headings)

class Contact(Persistent):
    __acl__    = [(Allow, Authenticated,   'view'),
                  (Allow, 'group:editor',  ['view', 'edit']),
                  (Allow, 'group:admin',   ALL_PERMISSIONS),
                  DENY_ALL]

    def __init__(self, name, contacts):
        Persistent.__init__(self)
        self.key           = contacts.maxKey() + 1
        self.__parent__    = contacts
        self.__name__      = self.key
        for heading in contacts.Headings:
            self.__setattr__(heading, "")
        self.name          = name
        contacts[self.key] = self


#---------------------------------------------------------------------------
# Contact Views
#---------------------------------------------------------------------------
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotImplemented
from pyramid.security import view_execution_permitted

from wtforms import Form
from wtforms.validators import required
from wtforms.fields import TextField, SubmitField

from .name   import chooseName, chooseAddress
from .pagination import Page
from .pagination import CatalogFieldIndexSlicer
from .formextras import SubmitBtn

class ContactForm(Form):
    name      = TextField(validators=[required()])
    address1  = TextField(u"Street")
    address2  = TextField(u"Suburb")
    city      = TextField()
    postCode  = TextField()
    country   = TextField()
    phone     = TextField()
    email     = TextField()

class ContactBtns(Form):
    okBtn     = SubmitField(u"OK",       widget=SubmitBtn())
    prevBtn   = SubmitField(u"Previous", widget=SubmitBtn())
    nextBtn   = SubmitField(u"Next",     widget=SubmitBtn())
    cancelBtn = SubmitField(u"Cancel",   widget=SubmitBtn())

class ContactsBtns(Form):
    addBtn    = SubmitField(u"Add Contact")
    delBtn    = SubmitField(u"Delete Contact")
    editBtn   = SubmitField(u"Edit Contact")


# TODO use interfaces?
# Specifying an interface instead of a class as the context or containment
# predicate arguments within view configuration statements makes it possible
# to use a single view callable for more than one class of resource object.

@view_config(context=Contacts,
             renderer='templates/contacts.pt',
             permission='view')
def viewContacts(contacts, request):
    btns = ContactsBtns()
    if request.method == 'POST': 
        btns.process(request.POST)
        selection = [ int(selected[7:]) for selected in request.POST
                                        if selected.startswith("select-") ]
        if btns.addBtn.data:
            url = request.resource_url(contacts, "@@add-contact")
            return HTTPFound(location = url)
        elif selection and btns.delBtn.data:
            contacts.delete(selection)
        elif selection and btns.editBtn.data:
            request.session['selectedContacts'] = selection
            contact = contacts.get(selection[0])
            if contact:
                url = request.resource_url(contact, "@@edit")
                return HTTPFound(location = url)
        else:
            return HTTPNotImplemented()
        url = request.resource_url(contacts).rstrip('/')
        return HTTPFound(location = url)

    form = ContactForm()
    headings = [(field.name, field.label.text) for field in form]
    rows = []

    pgParam = request.params.get("page", "1")
    current_page = int(pgParam)
    sortParam = request.params.get("sort", "")
    posCache = request.session.get('posCache', {})
    #FIXME currentIndex can't be stored in contacts
    if (sortParam and sortParam != contacts._currentIndex and 
        sortParam in contacts._cat):
        contacts._currentIndex = sortParam
        current_page = 1
        posCache.clear()
        
    numContacts = len(contacts)
    idx = contacts.getCurrentIndex()
    slicer = CatalogFieldIndexSlicer(idx, numContacts, posCache)
    page = Page(slicer, current_page, 10)
    request.session['posCache'] = posCache
    lastPg = (numContacts + 9) / 10

    for key in page:
        contact = contacts.get(key)
        if contact is None: continue
        form.process(obj=contact)
        # TODO use WTForms.BooleanField?
        checkbox = '<input type="checkbox" '\
                   'name="select-%d" value="" />'% key
        rows.append([checkbox, ]+[field.data for field in form])
    
    users    = request.root['users']
    projects = request.root['projects']
    return {'btns':        btns,
            'headings':    headings,
            'rows':        rows,
            'numContacts': numContacts,
            'pager':       '<a href="?page=1">1</a> ... '+
                           '<a href="?page=%d">%d</a>' % (lastPg, lastPg),
            'viewUsers'    : view_execution_permitted(users,    request),
            'viewContacts' : True,
            'viewProjects' : view_execution_permitted(projects, request),
            'currentUser': request.user}

@view_config(context=Contacts,
             xhr=True,
             renderer="json",
             permission='view')
def getContacts(contacts, request): 
    retval = {}
    return retval
    #echo = request.POST.get('sEcho')
    #retval['sEcho'] = str(int(echo))
    ##contacts = getAppRoot(request).get('contacts')

    #numContacts = len(contacts)
    #retval['iTotalRecords'] = numContacts
    #retval['iTotalDisplayRecords'] = numContacts

    #form = ContactForm()
    #rows = []
    #start  = int(request.POST.get('iDisplayStart'))
    #length = int(request.POST.get('iDisplayLength'))
    #for name, contact in contacts.items()[start:start+length]:
    #    form.process(obj=contact)
    #    checkbox = '<input type="checkbox" '\\
    #               'name="select-%s" value="" />'% name
    #    rows.append([checkbox, ]+[field.data for field in form])
    #    #row = dict(enumerate([field.data for field in form], start=1))
    #    #row[0] = checkbox
    #    #row['DT_RowId'] = name
    #    #rows.append(row)
    #retval['aaData'] = rows
    #return retval
           
@view_config(name="link",
             context=Contacts,
             renderer='templates/link_contact.pt',
             permission='view')
def linkContact(contacts, request):
    btns = ContactBtns()
    users    = request.root['users']
    projects = request.root['projects']

    if request.method == 'POST': 
        btns.process(request.POST)
        selection = [ selected[7:] for selected in request.POST
                                   if selected.startswith("select-") ]
        key = request.session['linkFromUser']
        user = users.get(key)
        if user is None:
            return HTTPNotImplemented()
        url = request.resource_url(user)
        if btns.okBtn.data:
            if selection:
                contact = contacts.get(selection[0])
                if not contact:
                    return HTTPNotImplemented()
                user.contact = (contact.key, contact.name)
            else:
                user.contact = None
            return HTTPFound(location = url)
        elif btns.cancelBtn.data:
            return HTTPFound(location = url)
        else:
            return HTTPNotImplemented()

    #TODO this is all common and shoule be reuseable
    form = ContactForm()
    headings = [(field.name, field.label.text) for field in form]
    rows = []

    pgParam = request.params.get("page", "1")
    current_page = int(pgParam)
    sortParam = request.params.get("sort", "")
    posCache = request.session.get('posCache', {})
    #FIXME currentIndex can't be stored in contacts
    if (sortParam and sortParam != contacts._currentIndex and 
        sortParam in contacts._cat):
        contacts._currentIndex = sortParam
        current_page = 1
        posCache.clear()
        
    numContacts = len(contacts)
    idx = contacts.getCurrentIndex()
    slicer = CatalogFieldIndexSlicer(idx, numContacts, posCache)
    page = Page(slicer, current_page, 10)
    #import pdb; pdb.set_trace()
    request.session['posCache'] = posCache
    lastPg = (numContacts + 9) / 10

    for key in page:
        contact = contacts.get(key)
        if contact is None: continue
        form.process(obj=contact)
        # TODO use WTForms.BooleanField?
        checkbox = '<input type="checkbox" '\
                   'name="select-%d" value="" />'% key
        rows.append([checkbox, ]+[field.data for field in form])
    
    return {'btns':        btns,
            'headings':    headings,
            'rows':        rows,
            'numContacts': numContacts,
            'pager':       '<a href="?page=1">1</a> ... '+
                           '<a href="?page=%d">%d</a>' % (lastPg, lastPg),
            'viewUsers'    : view_execution_permitted(users,    request),
            'viewContacts' : True,
            'viewProjects' : view_execution_permitted(projects, request),
            'currentUser': request.user}


@view_config(name='add-contact',
             context=Contacts,
             renderer='templates/edit_contact.pt',
             permission='edit')
def addContact(contacts, request):
    form = ContactForm()
    btns = ContactBtns()
    btns.prevBtn.flags.disabled = True
    btns.nextBtn.flags.disabled = False  # TODO support add-another
    users    = request.root['users']
    projects = request.root['projects']
    retval = {'form':         form,
              'btns':         btns,
              'viewUsers'    : view_execution_permitted(users,    request),
              'viewContacts' : True,
              'viewProjects' : view_execution_permitted(projects, request),
              'currentUser':  request.user}
    if request.method == 'POST':
        form.process(request.POST)
        btns.process(request.POST)
        if btns.cancelBtn.data:
            url = request.resource_url(contacts).rstrip('/')
            return HTTPFound(location = url)
        elif btns.okBtn.data:
            if not form.validate():
                return retval
            # Create a new Contact
            contact = Contact(form.name.data, contacts)
            form.populate_obj(contact)
            contacts.reindex(contact)
            url = request.resource_url(contact).rstrip('/')
            return HTTPFound(location = url)
        else:
            return HTTPNotImplemented()

    return retval

@view_config(context=Contact,
             renderer='templates/contact.pt',
             permission='view')
def viewContact(contact, request):
    form = ContactForm(obj=contact)
    users    = request.root['users']
    projects = request.root['projects']
    return {'form':        form,
            'viewUsers'    : view_execution_permitted(users,    request),
            'viewContacts' : True,
            'viewProjects' : view_execution_permitted(projects, request),
            'currentUser': request.user}

@view_config(name='edit',
             context=Contact,
             renderer='templates/edit_contact.pt',
             permission='edit')
def editContact(contact, request):
    contacts = request.root['contacts']
    # or contact.__parent__ ?
    # or find_interface(Users) ?
    form = ContactForm(obj=contact)
    btns = ContactBtns()
    selection = request.session.get('selectedContacts', [])
    myPos = None
    btns.prevBtn.flags.disabled = True
    btns.nextBtn.flags.disabled = True
    try:
        myPos = selection.index(contact.key)
        if myPos > 0:
            btns.prevBtn.flags.disabled = False
        if myPos < len(selection) - 1:
            btns.nextBtn.flags.disabled = False
    except ValueError:
        pass
    referer = request.get('HTTP_REFERER', request.url)
    users    = request.root['users']
    projects = request.root['projects']
    retval = {'form':         form,
              'btns':         btns,
              'came_from':    referer,
              'viewUsers'    : view_execution_permitted(users,    request),
              'viewContacts' : True,
              'viewProjects' : view_execution_permitted(projects, request),
              'currentUser':  request.user}


    if request.method == 'POST':
        if 'came_from' in request.params:
            retval['came_from'] = request.params['came_from']
        form.process(request.POST)
        btns.process(request.POST)
        if btns.cancelBtn.data:
            # go back if you can
            url = request.params.get('came_from', 
                                     request.resource_url(contact).rstrip('/'))
            return HTTPFound(location = url)
        elif btns.okBtn.data:
            request.session['selectedContacts'] = []
            url = request.resource_url(contact).rstrip('/')
        elif btns.prevBtn.data and not btns.prevBtn.flags.disabled:
            selected = selection[myPos - 1]
            url = request.resource_url(contacts, selected, "@@edit")
        elif btns.nextBtn.data and not btns.nextBtn.flags.disabled:
            selected = selection[myPos + 1]
            url = request.resource_url(contacts, selected, "@@edit")
        else:
            return HTTPNotImplemented()

        if not form.validate():
            return retval
        # Update an existing Contact
        form.populate_obj(contact)
        contacts.reindex(contact)
        return HTTPFound(location = url)

    return retval

@view_config(name='add-test-data',
             context=Contacts,
             permission='edit')
def addTestData(contacts, request):
    for i in  range(10000):
        contact = Contact(chooseName(), contacts)
        street, district, city = chooseAddress()
        contact.address1 = street
        contact.address2 = district
        contact.city     = city
        contacts.reindex(contact)
    return Response('Done!')


