from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
from persistent import Persistent
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid_zodbconn import get_connection
import transaction

def findUniqueId(parent, name):
    """This is a blatent ripoff of the function in Archetypes"""
    name = name.replace(' ', '-')
    if parent is None:
        parent = []
    myId = name
    index = 0
    while myId in parent:
        index += 1
        if index > 2000:
            raise IndexError
        myId = "%s-%d" % (name, index) 
    return myId

class AppRoot(PersistentMapping):
    __name__   = None
    __parent__ = None
    __acl__    = [(Allow, Authenticated,   'view')]

    def __init__(self):
        PersistentMapping.__init__(self)
        Contacts(self)
        Projects(self)

# TODO inherit from OOBTree instead of PersistentMapping?
class AppModule(PersistentMapping):
    def __init__(self, parent):
        PersistentMapping.__init__(self)
        self.__parent__  = parent
        parent[self.__name__] = self

    def delete(self, names):
        for name in names:
            if name in self:
                del self[name]

class Contacts(AppModule):
    __acl__    = [(Allow, Authenticated, 'view'),
                  (Allow, 'group:editors', 'edit')]
    __name__   = 'contacts'

    def __init__(self, parent):
        AppModule.__init__(self, parent)

class Projects(AppModule):
    __acl__    = [(Allow, Authenticated, 'view'),
                  (Allow, 'group:editors', 'edit')]
    __name__   = 'projects'

    def __init__(self, parent):
        AppModule.__init__(self, parent)
        
class Contact(Persistent):
    __acl__    = [(Allow, Authenticated, 'view'),
                  (Allow, 'group:editors', 'edit')]

    def __init__(self, name, parent):
        Persistent.__init__(self)
        myId = findUniqueId(parent, name)
        self.__parent__ = parent
        self.__name__   = myId
        self.name       = name
        parent[myId]    = self

    def getId(self):
        return self.__name__
        
class Project(PersistentList):
    __acl__    = [(Allow, Authenticated, 'view'),
                  (Allow, 'group:editors', 'edit')]

    def __init__(self, name, parent):
        Persistent.__init__(self)
        myId = findUniqueId(parent, name)
        self.__parent__ = parent
        self.__name__   = myId
        self.name       = name
        parent[myId]    = self

    def getId(self):
        return self.__name__

class Task(Persistent):
    pass

def getAppRoot(request):
    dbRoot = get_connection(request).root()
    if not 'djoser' in dbRoot:
        dbRoot['djoser'] = AppRoot()
        transaction.commit()
    return dbRoot['djoser']


