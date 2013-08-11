# ------------------------------------------------------------------------------
# User Resources
# ------------------------------------------------------------------------------
from persistent import Persistent
from persistent.list import PersistentList
from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS
from pyramid.security import DENY_ALL
from pyramid.security import unauthenticated_userid
from random import randint
from passlib.utils import generate_password
from passlib.context import CryptContext

from .table import Table

# Groups are hardcoded for now
Groups = {"group:guest":    "Guest",
          "group:member":   "Member",
          "group:editor":   "Editor",
          "group:admin":    "Admin"}

def checkAuthentication(name, givenPass, request):
    users = request.root['users']
    user = users.getByName(name)
    if user:
        return user.verifyPassword(givenPass)
    else:
        return False

# from http://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/auth/user_object.html

def getUser(request):
    name = unauthenticated_userid(request)
    if name is not None:
        users = request.root['users']
        return users.getByName(name)

def getGroups(name, request):
    user = request.user
    if user is not None:
        return user.groups
    else:
        return None

#def getGroups(name, request):
#    from .app import getAppRoot
#    users = getAppRoot(request).get('users')
#    user = users.getByName(name)
#    if user is not None:
#        return user.groups
#    else:
#        return None


class Users(Table):
    __acl__    = [(Allow, 'group:admin', ALL_PERMISSIONS),
                  DENY_ALL]
    __name__   = 'users'

    def __init__(self, parent):
        Table.__init__(self, parent, ['name'])
        # create the root user
        randPass = generate_password(randint(12,18))
        root = User('root', self)
        root.password = randPass
        root.groups   = ['group:admin']
        self.reindex(root)
        print "#%d %s:%s" % (root.key, root.name, randPass)

    def getByName(self, name):
        users = self.getFromIndex('name', name)
        if len(users) >= 1:
            return users[0]


class User(Persistent):
    __acl__    = [(Allow, 'group:admin', ALL_PERMISSIONS),
                  DENY_ALL]
    PassContext = CryptContext(schemes=["sha512_crypt"])

    def __init__(self, name, users):
        Persistent.__init__(self)
        self.key        = users.maxKey() + 1
        self.__parent__ = users
        self.__name__   = self.key
        self.name       = name
        self._passHash  = ""
        self._groups    = PersistentList()
        self.contact    = None
        users[self.key] = self

    def _setPassword(self, password):
        self._passHash  = User.PassContext.encrypt(password)
    password = property(None, _setPassword)

    def verifyPassword(self, givenPass):
        return User.PassContext.verify(givenPass, self._passHash)

    def _getGroups(self):
        return self._groups
    def _setGroups(self, groups):
        self._groups = PersistentList(groups)
    groups = property(_getGroups, _setGroups)


#---------------------------------------------------------------------------
# User Views
#---------------------------------------------------------------------------
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotImplemented
from pyramid.security import view_execution_permitted

from wtforms import Form
from wtforms.validators import required
from wtforms.fields import TextField, PasswordField
from wtforms.fields import SubmitField, SelectMultipleField

from .name       import chooseName
from .pagination import Page
from .pagination import CatalogFieldIndexSlicer
from .formextras import SubmitBtn

class UserForm(Form):
    name      = TextField(validators=[required()])
    password  = PasswordField()
    groups    = SelectMultipleField(choices=Groups.items())
    contact   = TextField()

class UserBtns(Form):
    okBtn     = SubmitField(u"OK",       widget=SubmitBtn())
    prevBtn   = SubmitField(u"Previous", widget=SubmitBtn())
    nextBtn   = SubmitField(u"Next",     widget=SubmitBtn())
    cancelBtn = SubmitField(u"Cancel",   widget=SubmitBtn())
    linkBtn   = SubmitField(u"Link Contact")

class UsersBtns(Form):
    addBtn    = SubmitField(u"Add User")
    delBtn    = SubmitField(u"Delete User")
    editBtn   = SubmitField(u"Edit User")

@view_config(context=Users,
             renderer='templates/users.pt',
             permission='view')
def viewUsers(users, request):
    from pyramid.security import principals_allowed_by_permission
    print "allowed to", principals_allowed_by_permission(Users, 'view')
    btns = UsersBtns()
    if request.method == 'POST': 
        btns.process(request.POST)
        selection = [ selected[7:] for selected in request.POST
                                   if selected.startswith("select-") ]
        if btns.addBtn.data:
            url = request.resource_url(users, "@@add-user")
            return HTTPFound(location = url)
        elif selection and btns.delBtn.data:
            users.delete(selection)
        elif selection and btns.editBtn.data:
            request.session['selectedUsers'] = selection
            user = users.get(selection[0])
            if user:
                url = request.resource_url(user, "@@edit")
                return HTTPFound(location = url)
        else:
            return HTTPNotImplemented()
        url = request.resource_url(users).rstrip('/')
        return HTTPFound(location = url)


    pgParam = request.params.get("page", "1")
    current_page = int(pgParam)
    sortParam = request.params.get("sort", "")
    posCache = request.session.get('posCache', {})
    #FIXME currentIndex can't be stored in users
    if (sortParam and sortParam != users._currentIndex and 
        sortParam in users._cat):
        users._currentIndex = sortParam
        current_page = 1
        posCache.clear()
        
    numUsers = len(users)
    idx = users.getCurrentIndex()
    slicer = CatalogFieldIndexSlicer(idx, numUsers, posCache)
    page = Page(slicer, current_page, 10)
    request.session['posCache'] = posCache
    lastPg = (numUsers + 9) / 10

    #form = UserForm()
    rows = []
    for key in page:
        user = users.get(key)
        if user is None: continue
        #form.process(obj=user)
        name = user.name
        # TODO use BooleanField?
        checkbox = '<input type="checkbox" '\
                   'name="select-%d" value="" />' % key
        groups = ", ".join(Groups[grp] for grp in user.groups)
        contact = ""
        if user.contact:
            contact = '<a href="/contacts/%d">%s</a>' % user.contact
        rows.append([checkbox, name, groups, contact])
    
    contacts = request.root['contacts']
    projects = request.root['projects']
    #TODO move viewUsers,viewContacts,viewProjects into the User object
    return {'btns':        btns,
            'rows':        rows,
            'numUsers': numUsers,
            'pager':       '<a href="?page=1">1</a> ... '+
                           '<a href="?page=%d">%d</a>' % (lastPg, lastPg),
            'viewUsers'    : True,
            'viewContacts' : view_execution_permitted(contacts, request),
            'viewProjects' : view_execution_permitted(projects, request),
            'currentUser'  : request.user}

#@view_config(context=Users,
#             xhr=True,
#             renderer="json",
#             permission='view')
#def getUsers(users, request): 
#    retval = {}
#    return retval
           

@view_config(name='add-user',
             context=Users,
             renderer='templates/edit_user.pt',
             permission='edit')
def addUser(users, request):
    form = UserForm()
    btns = UserBtns()
    contacts = request.root['contacts']
    projects = request.root['projects']
    retval = {'form'         : form,
              'btns'         : btns,
              'viewUsers'    : True,
              'viewContacts' : view_execution_permitted(contacts, request),
              'viewProjects' : view_execution_permitted(projects, request),
              'currentUser'  : request.user}
    if request.method == 'POST':
        form.process(request.POST)
        btns.process(request.POST)
        if btns.cancelBtn.data:
            url = request.resource_url(users).rstrip('/')
            return HTTPFound(location = url)
        elif btns.okBtn.data:
            if not form.validate():
                return retval
            # Create a new User
            user = User(form.name.data, users)
            form.populate_obj(user)
            users.reindex(user)
            url = request.resource_url(user).rstrip('/')
            return HTTPFound(location = url)
        elif btns.linkBtn.data:
            request.session['linkFromUser'] = user.key
            url = request.resource_url(contacts, "@@link")
            return HTTPFound(location = url)
        else:
            return HTTPNotImplemented()

    return retval

@view_config(context=User,
             renderer='templates/user.pt',
             permission='view')
def viewUser(user, request):
    form = UserForm(obj=user)
    return {'form':        form,
            'currentUser': request.user}

@view_config(name='edit',
             context=User,
             renderer='templates/edit_user.pt',
             permission='edit')
def editUser(user, request):
    users = request.root['users']
    # or user.__parent__ ?
    form = UserForm(obj=user)
    btns = UserBtns()
    selection = request.session.get('selectedUsers', [])
    myPos = None
    btns.prevBtn.flags.disabled = True
    btns.nextBtn.flags.disabled = True
    try:
        myPos = selection.index(user.key)
        if myPos > 0:
            btns.prevBtn.flags.disabled = False
        if myPos < len(selection) - 1:
            btns.nextBtn.flags.disabled = False
    except ValueError:
        pass
    contacts = request.root['contacts']
    projects = request.root['projects']
    retval = {'form'         : form,
              'btns'         : btns,
              'viewUsers'    : True,
              'viewContacts' : view_execution_permitted(contacts, request),
              'viewProjects' : view_execution_permitted(projects, request),
              'currentUser'  : request.user}

    if request.method == 'POST':
        form.process(request.POST)
        btns.process(request.POST)
        if btns.cancelBtn.data:
            del request.session['linkFromUser']
            url = request.resource_url(user).rstrip('/')
            return HTTPFound(location = url)
        elif btns.okBtn.data:
            request.session['selectedUsers'] = []
            url = request.resource_url(user).rstrip('/')
        elif btns.prevBtn.data and not btns.prevBtn.flags.disabled:
            selected = selection[myPos - 1]
            url = request.resource_url(users, selected, "@@edit")
        elif btns.nextBtn.data and not btns.nextBtn.flags.disabled:
            selected = selection[myPos + 1]
            url = request.resource_url(users, selected, "@@edit")
        elif btns.linkBtn.data:
            request.session['linkFromUser'] = user.key
            url = request.resource_url(contacts, "@@link")
            return HTTPFound(location = url)
        else:
            return HTTPNotImplemented()

        if not form.validate():
            return retval
        # Update an existing User
        form.populate_obj(user)
        users.reindex(user)
        return HTTPFound(location = url)

    return retval

@view_config(name='add-test-data',
             context=Users,
             permission='edit')
def addTestData(users, request):
    for i in  range(100):
        randPass = generate_password(randint(12, 18))
        user = User(chooseName(), users)
        user.password = randPass
        users.reindex(user)
    return Response('Done!')


