# ------------------------------------------------------------------------------
# Application Models
# ------------------------------------------------------------------------------
from persistent.mapping import PersistentMapping
from persistent import Persistent
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid_zodbconn import get_connection
from BTrees.IOBTree import IOBTree
from repoze.catalog.catalog import Catalog
import transaction

from . import contacts
from . import projects

class AppRoot(PersistentMapping):
    __name__   = None
    __parent__ = None
    __acl__    = [(Allow, Authenticated,   'view')]

    def __init__(self):
        PersistentMapping.__init__(self)
        contacts.Contacts(self)
        projects.Projects(self)

def getAppRoot(request):
    dbRoot = get_connection(request).root()
    if not 'djoser' in dbRoot:
        dbRoot['djoser'] = AppRoot()
        transaction.commit()
    return dbRoot['djoser']

# ------------------------------------------------------------------------------
# Application Views
# ------------------------------------------------------------------------------
from pyramid.view import view_config
from pyramid.view import forbidden_view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotImplemented
from pyramid.security import remember
from pyramid.security import forget
from pyramid.security import authenticated_userid

from .security import checkAuthentication

@view_config(context=AppRoot,
             renderer='templates/root.pt',
             permission='view')
def viewRoot(request):
    return {'currentUser': authenticated_userid(request)}

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

@view_config(context=AppRoot, name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location = request.resource_url(request.context),
                     headers = headers)


#---------------------------------------------------------------------------
# reprompt for basic authentication upon 403s
#@view_config(context=HTTPForbidden)
#def basic_challenge(request):
#    response = HTTPUnauthorized()
#    response.headers.update(forget(request))
#    return response
#---------------------------------------------------------------------------

