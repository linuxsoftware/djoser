# ------------------------------------------------------------------------------
# Project Models
# ------------------------------------------------------------------------------
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
from persistent import Persistent
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid_zodbconn import get_connection
from BTrees.IOBTree import IOBTree
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.text import CatalogTextIndex
import transaction

from .module import Module

class Projects(Module):
    __acl__    = [(Allow, Authenticated,   'view'),
                  (Allow, 'group:editors', 'edit')]
    __name__   = 'projects'

    def __init__(self, parent):
        Module.__init__(self, parent)
        
class Project(PersistentList):
    __acl__    = [(Allow, Authenticated,   'view'),
                  (Allow, 'group:editors', 'edit')]

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

class ProjectForm(Form):
    name     = TextField(validators=[required()])

@view_config(context=Projects,
             renderer='templates/projects.pt',
             permission='view')
def viewProjects(projects, request):
    if request.method == 'POST': 
        pass
    else:
        form = ProjectForm()
        rows = []
        for name, project in projects.items():
            form.process(obj=project)
            rows.append([name, ]+[field.data for field in form])
        return {'rows':        rows,
                'currentUser': authenticated_userid(request)}

