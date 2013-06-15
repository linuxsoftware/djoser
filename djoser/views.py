from pyramid.view import view_config
from pyramid.view import forbidden_view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotImplemented
from pyramid.security import remember
from pyramid.security import forget
from pyramid.security import authenticated_userid

from wtforms import Form
from wtforms.validators import required
from wtforms.fields import TextField, SubmitField
from wtforms.widgets import SubmitInput

import webhelpers.paginate as paginate

from .models import AppRoot
from .models import getAppRoot

from .security import checkAuthentication

#---------------------------------------------------------------------------
# AppRoot
#---------------------------------------------------------------------------
@view_config(context=AppRoot,
             renderer='templates/root.pt',
             permission='view')
def viewRoot(request):
    return {'currentUser': authenticated_userid(request)}

#---------------------------------------------------------------------------
# Contact Views
#---------------------------------------------------------------------------
from .models import Contacts
from .models import Contact
from .name   import chooseName, chooseAddress

class ContactForm(Form):
    name      = TextField(validators=[required()])
    address1  = TextField(u"Street")
    address2  = TextField(u"Suburb")
    city      = TextField()
    postCode  = TextField()
    country   = TextField()
    phone     = TextField()
    email     = TextField()

class SubmitBtn(SubmitInput):
    def __call__(self, field, **kwargs):
        if field.flags.disabled:
            kwargs.setdefault("disabled", True)
        return SubmitInput.__call__(self, field, **kwargs)

class ContactBtns(Form):
    okBtn     = SubmitField(u"OK",       widget=SubmitBtn())
    prevBtn   = SubmitField(u"Previous", widget=SubmitBtn())
    nextBtn   = SubmitField(u"Next",     widget=SubmitBtn())
    cancelBtn = SubmitField(u"Cancel",   widget=SubmitBtn())

class ContactsBtns(Form):
    addBtn    = SubmitField(u"Add Contact")
    delBtn    = SubmitField(u"Delete Contact")
    editBtn   = SubmitField(u"Edit Contact")

@view_config(context=Contacts,
             renderer='templates/contacts.pt',
             permission='view')
def viewContacts(contacts, request):
    btns = ContactsBtns()
    if request.method == 'POST': 
        btns.process(request.POST)
        selection = [ selected[7:] for selected in request.POST
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
    headings = [field.label.text for field in form]
    rows = []
    numContacts = len(contacts)
    current_page = int(request.params.get("page", 1))
    page_url = paginate.PageURL_WebOb(request)
    page = paginate.Page(contacts.items(), current_page,
                            items_per_page=10, item_count=numContacts,
                            url=page_url)
    # print page
    

    for name, contact in page:
        form.process(obj=contact)
        # TODO use BooleanField?
        checkbox = '<input type="checkbox" '\
                   'name="select-%s" value="" />'% name
        rows.append([checkbox, ]+[field.data for field in form])
    
    return {'btns':        btns,
            'headings':    headings,
            'rows':        rows,
            'numContacts': numContacts,
            'pager':       page.pager(),
            'currentUser': authenticated_userid(request)}

@view_config(context=Contacts,
             xhr=True,
             renderer="json",
             permission='view')
def getContacts(contacts, request): 
    retval = {}
    echo = request.POST.get('sEcho')
    retval['sEcho'] = str(int(echo))
    #contacts = getAppRoot(request).get('contacts')
    numContacts = len(contacts)
    retval['iTotalRecords'] = numContacts
    retval['iTotalDisplayRecords'] = numContacts

    form = ContactForm()
    rows = []
    start  = int(request.POST.get('iDisplayStart'))
    length = int(request.POST.get('iDisplayLength'))
    # TODO use OOBTree? or IOBTree?
    for name, contact in contacts.items()[start:start+length]:
        form.process(obj=contact)
        checkbox = '<input type="checkbox" '\
                   'name="select-%s" value="" />'% name
        rows.append([checkbox, ]+[field.data for field in form])
        #row = dict(enumerate([field.data for field in form], start=1))
        #row[0] = checkbox
        #row['DT_RowId'] = name
        #rows.append(row)
    retval['aaData'] = rows
    return retval
           

@view_config(name='add-contact',
             context=Contacts,
             renderer='templates/edit_contact.pt',
             permission='edit')
def addContact(contacts, request):
    form = ContactForm()
    btns = ContactBtns()
    retval = {'form':         form,
              'btns':         btns,
              'currentUser':  authenticated_userid(request)}
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
    return {'form':        form,
            'currentUser': authenticated_userid(request)}

@view_config(name='edit',
             context=Contact,
             renderer='templates/edit_contact.pt',
             permission='edit')
def editContact(contact, request):
    contacts = getAppRoot(request).get('contacts')
    # or contact.__parent__ ?
    form = ContactForm(obj=contact)
    btns = ContactBtns()
    selection = request.session.get('selectedContacts', [])
    myPos = None
    btns.prevBtn.flags.disabled = True
    btns.nextBtn.flags.disabled = True
    try:
        myPos = selection.index(contact.getId())
        if myPos > 0:
            btns.prevBtn.flags.disabled = False
        if myPos < len(selection) - 1:
            btns.nextBtn.flags.disabled = False
    except ValueError:
        pass
    retval = {'form':         form,
              'btns':         btns,
              'currentUser':  authenticated_userid(request)}

    if request.method == 'POST':
        form.process(request.POST)
        btns.process(request.POST)
        if btns.cancelBtn.data:
            url = request.resource_url(contact).rstrip('/')
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
        return HTTPFound(location = url)

    return retval

@view_config(name='add-test-data',
             context=Contacts,
             permission='edit')
def addTestData(contacts, request):
    for i in range(100):
        contact = Contact(chooseName(), contacts)
        street, district, city = chooseAddress()
        contact.address1 = street
        contact.address2 = district
        contact.city     = city
    return Response('Done!')

#---------------------------------------------------------------------------
# Project Views
#---------------------------------------------------------------------------
from .models import Projects
from .models import Project

class ProjectForm(Form):
    name     = TextField(validators=[required()])

@view_config(context=Projects,
             renderer='templates/projects.pt',
             permission='view')
def viewProjects(projects, request):
    if request.method == 'POST': 
        pass
    else:
        form = ContactForm()
        rows = []
        for name, project in projects.items():
            form.process(obj=project)
            rows.append([name, ]+[field.data for field in form])
        return {'rows':        rows,
                'currentUser': authenticated_userid(request)}

#---------------------------------------------------------------------------
# AJAX demo
#---------------------------------------------------------------------------
from random import randint
@view_config(context=Projects,
             xhr=True,
             renderer="json",
             permission='view')
def updates_view(projects, request):
    return [
        randint(0,100),
        randint(0,100),
        randint(0,100),
        randint(0,100),
        888,
    ]

#---------------------------------------------------------------------------
# Login
#---------------------------------------------------------------------------
@view_config(context=AppRoot, name='login',
             renderer='templates/login.pt')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):
    login_url = request.resource_url(request.context, 'login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)
    message = ''
    login = ''
    password = ''
    if 'form.submitted' in request.params:
        login = request.params['login']
        password = request.params['password']
        if checkAuthentication(login, password, request) is not None:
            headers = remember(request, login)
            return HTTPFound(location = came_from,
                             headers  = headers)
        message = 'Failed login'

    return dict(message   = message,
                url       = request.application_url + '/login',
                came_from = came_from,
                login     = login,
                password  = password,
                currentUser = None)

#---------------------------------------------------------------------------
# Logout
#---------------------------------------------------------------------------
@view_config(context=AppRoot, name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location = request.resource_url(request.context),
                     headers = headers)


#---------------------------------------------------------------------------
# reprompt for basic authentication upon 403s
#---------------------------------------------------------------------------
#@view_config(context=HTTPForbidden)
#def basic_challenge(request):
#    response = HTTPUnauthorized()
#    response.headers.update(forget(request))
#    return response

