# ------------------------------------------------------------------------------
# Application Resources
# ------------------------------------------------------------------------------
from persistent.mapping import PersistentMapping
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import DENY_ALL
from pyramid_zodbconn import get_connection
import transaction

from .users    import Users
from .contacts import Contacts
from .projects import Projects

class AppRoot(PersistentMapping):
    __name__   = ""
    __parent__ = None
    __acl__    = [(Allow, Authenticated,   'view'),
                  DENY_ALL]

    def __init__(self):
        PersistentMapping.__init__(self)
        Contacts(self)
        Projects(self)
        Users(self)

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
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from pyramid.security import forget
from pyramid.security import view_execution_permitted
from .users import checkAuthentication

@view_config(context=AppRoot,
             renderer='templates/root.pt',
             permission='view')
def viewRoot(root, request):
    return {'viewUsers'    : view_execution_permitted(root['users'],    request),
            'viewContacts' : view_execution_permitted(root['contacts'], request),
            'viewProjects' : view_execution_permitted(root['projects'], request),
            'currentUser'  : request.user}

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
        #TODO pull up a user object
        if checkAuthentication(login, password, request):
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

