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
from wtforms.fields import TextField

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
    name     = TextField(validators=[required()])
    address1 = TextField(u"Street")
    address2 = TextField(u"Suburb")
    city     = TextField()
    postCode = TextField()
    country  = TextField()
    phone    = TextField()
    email    = TextField()

@view_config(context=Contacts,
             renderer='templates/contacts.pt',
             permission='view')
def viewContacts(contacts, request):
    if request.method == 'POST': 
        selection = [ selected[7:] for selected in request.POST
                                   if selected.startswith("select-") ]
        if 'add-contact' in request.POST:
            url = request.resource_url(contacts, "@@add-contact")
            return HTTPFound(location = url)
        elif selection and 'delete-contact' in request.POST:
            contacts.delete(selection)
        elif selection and 'edit-contact' in request.POST:
            request.session['selectedContacts'] = selection
            contact = contacts.get(selection[0])
            if contact:
                url = request.resource_url(contact, "@@edit")
                return HTTPFound(location = url)
        url = request.resource_url(contacts).rstrip('/')
        return HTTPFound(location = url)

    form = ContactForm()
    headings = [field.label.text for field in form]
    rows = []
    for name, contact in contacts.items():
        form.process(obj=contact)
        rows.append([name, ]+[field.data for field in form])
    
    return {'headings':    headings,
            'rows':        rows,
            'currentUser': authenticated_userid(request)}

@view_config(name='add-contact',
             context=Contacts,
             renderer='templates/edit_contact.pt',
             permission='edit')
def addContact(contacts, request):
    form = ContactForm(request.POST)
    retval = {'form': form,
              'prevDisabled': "disabled",
              'nextDisabled': "disabled",
              'currentUser':  authenticated_userid(request)}
    if request.method == 'POST':
        if 'OK' in request.POST:
            if not form.validate():
                return retval
            # Create a new Contact
            contact = Contact(form.name.data, contacts)
            form.populate_obj(contact)
        url = request.resource_url(contact).rstrip('/')
        return HTTPFound(location = url)
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
    form = ContactForm(request.POST, contact)
    selection = request.session.get('selectedContacts', [])
    myPos = None
    prevDisabled = "disabled"
    nextDisabled = "disabled"
    try:
        myPos = selection.index(contact.getId())
        if myPos > 0:
            prevDisabled = None
        if myPos < len(selection) - 1:
            nextDisabled = None
    except ValueError:
        pass
    retval = {'form':         form,
              'prevDisabled': prevDisabled,
              'nextDisabled': nextDisabled,
              'currentUser':  authenticated_userid(request)}

    if request.method == 'POST':
        if 'Cancel' in request.POST:
            url = request.resource_url(contact, "@@edit")
            return HTTPFound(location = url)
        elif 'OK' in request.POST:
            request.session['selectedContacts'] = []
            url = request.resource_url(contact).rstrip('/')
        elif not prevDisabled and 'Prev' in request.POST:
            selected = selection[myPos - 1]
            url = request.resource_url(contacts, selected, "@@edit")
        elif not nextDisabled and 'Next' in request.POST:
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

