# ------------------------------------------------------------------------------
# Project Models
# ------------------------------------------------------------------------------
from persistent.list import PersistentList
from persistent import Persistent
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import ALL_PERMISSIONS
from pyramid.security import DENY_ALL

from .table import Table

class Projects(Table):
    __acl__    = [(Allow, Authenticated,   'view'),
                  (Allow, 'group:editor',  ['view', 'edit']),
                  (Allow, 'group:admin',   ALL_PERMISSIONS),
                  DENY_ALL]
    __name__   = 'projects'

    def __init__(self, parent):
        Table.__init__(self, parent)
        
class Project(PersistentList):
    __acl__    = [(Allow, Authenticated,   'view'),
                  (Allow, 'group:editor',  ['view', 'edit']),
                  (Allow, 'group:admin',   ALL_PERMISSIONS),
                  DENY_ALL]

    def __init__(self, name, parent):
        Persistent.__init__(self)
        #resId = findUniqueId(parent, name)
        self.__parent__ = parent
        #self.__name__   = resId
        self.name       = name
        #parent[resId]   = self

    def getId(self):
        return self.__name__

class Task(Persistent):
    pass

class Note(Persistent):
    pass


# ------------------------------------------------------------------------------
# Project Views
# ------------------------------------------------------------------------------
from pyramid.view import view_config
from pyramid.security import view_execution_permitted

from wtforms import Form
from wtforms.validators import required
from wtforms.fields import TextField


class ProjectForm(Form):
    name     = TextField(validators=[required()])

@view_config(context=Projects,
             renderer='templates/projects.pt',
             permission='view')
def viewProjects(projects, request):
    users    = request.root['users']
    contacts = request.root['contacts']
    rows = []
    if request.method == 'POST': 
        pass
    else:
        form = ProjectForm()
        for name, project in projects.items():
            form.process(obj=project)
            rows.append([name, ]+[field.data for field in form])
        root = request.root
    return {'rows':        rows,
            'viewUsers'    : view_execution_permitted(users,    request),
            'viewContacts' : view_execution_permitted(contacts, request),
            'viewProjects' : True,
            'currentUser'  : request.user}

