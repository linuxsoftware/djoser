from pyramid.view import view_config
from pyramid.view import forbidden_view_config
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from pyramid.security import forget
from pyramid.security import authenticated_userid

import colander
from colander import MappingSchema
from colander import SequenceSchema
from colander import SchemaNode
from colander import Schema
from colander import String
from colander import Boolean
from colander import Integer
from colander import Length
from colander import OneOf

from deform import ValidationFailure
from deform import Form
from deform import widget

from .models import AppRoot
from .models import Contacts
from .models import Contact

from .security import checkAuthentication

#---------------------------------------------------------------------------
# AppRoot
#---------------------------------------------------------------------------
@view_config(context=AppRoot,
             renderer='templates/root.pt',
             permission='view')
def viewRoot(request):
    return {'project': 'd3',
            'currentUser': authenticated_userid(request)}

#---------------------------------------------------------------------------
# Contacts
#---------------------------------------------------------------------------
@view_config(context=Contacts,
             renderer='templates/contacts.pt',
             permission='view')
def viewContacts(request):
    return {'project': 'd3',
            'currentUser': authenticated_userid(request)}

#---------------------------------------------------------------------------
# Contact
#---------------------------------------------------------------------------
class ContactSchema(Schema):
    name     = SchemaNode(String())
    address1 = SchemaNode(String(), missing=u'')
    address2 = SchemaNode(String(), missing=u'')
    city     = SchemaNode(String(), missing=u'')
    postCode = SchemaNode(String(), missing=u'')
    country  = SchemaNode(String(), missing=u'')
    phone    = SchemaNode(String(), missing=u'')
    email    = SchemaNode(String(), missing=u'')

@view_config(name='add-contact',
             context=Contacts,
             renderer='templates/edit_contact.pt',
             permission='edit')
def addContact(context, request):
    schema = ContactSchema()
    form = Form(schema, buttons=('submit',))
    if 'submit' in request.POST:
        controls = request.POST.items()
        try:
            appstruct = form.validate(controls)
        except ValidationFailure, e:
            return {'form': e.render(),
                    'currentUser': authenticated_userid(request)}

        # Make a new Contact
        contact = Contact(appstruct['name'], context)
        url = request.resource_url(contact).rstrip('/')
        return HTTPFound(location = url)

    else:
        return {'form':  form.render(),
                'currentUser': authenticated_userid(request)}

    #    # Make a new Contact
    #    body = request.params['body']
    #    contact = Contact()
    #    contact.__name__   = name
    #    contact.__parent__ = context
    #    context[name] = contact
    #    return HTTPFound(location = request.resource_url(contact))
    #save_url = request.resource_url(context, 'add-contact', name)
    #contact = Contact('')
    ##logged_in = authenticated_userid(request)
    #return dict(contact      = contact,
    #            save_url     = save_url)

@view_config(context=Contact,
             renderer='templates/contact.pt',
             permission='view')
def viewContact(request):
    return {'project': 'd3',
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
                password  = password,)

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

