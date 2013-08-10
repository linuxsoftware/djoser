# ------------------------------------------------------------------------------
# Table base class
# ------------------------------------------------------------------------------
from zc.dict.dict import Dict as ZopeDict
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.query import Eq

class Table(ZopeDict):
    """
    A table is a combination of a ZopeDict and a RepozeCatalog
    with integer keys and object values
    """
    #TODO write my own IOBTree/Length combination instead of using ZopeDict?
    def __init__(self, parent, indices=None):
        ZopeDict.__init__(self)
        self.__parent__  = parent
        parent[self.__name__] = self
        self._cat = Catalog()
        if indices is None:
            self._currentIndex = ""
        else:
            self._currentIndex = indices[0]
            for index in indices:
                self._cat[index] = CatalogFieldIndex(index)

    def getCurrentIndex(self):
        # FIXME current index should be part of the user preferences
        return self._cat[self._currentIndex]

    def delete(self, names):
        print "TODO delete"
        pass

    def getFromIndex(self, index, target):
        # TODO return a generator instead of a list
        retval = []
        result = self._cat.query(Eq(index, target))
        for key in result[1]:
            user = self.get(key)
            if user:
                retval.append(user)
        return retval

    def maxKey(self):
        return self._data.maxKey() if len(self) else 0


    # NB I have to cast key to an int for traversal to work
    # FIXME: it seems like this is the wrong place for this maybe it 
    # is a sign I should give up on traversal altogether?
    def __getitem__(self, key):
        return self._data[int(key)]

    def setdefault(self, key, failobj=None):
        return ZopeDict.setdefault(self, int(key), failobj)

    def has_key(self, key):
        return ZopeDict.has_key(self, int(key))

    def get(self, key, failobj=None):
        return ZopeDict.get(self, int(key), failobj)

    def __contains__(self, key):
        return ZopeDict.__contains__(self, int(key))
    
    # zc.dict interface
    # Addition is done with __setitem__, overriding it will control addition.
    def __setitem__(self, key, value):
        #self._cat.index_doc(int(key), value)
        ZopeDict.__setitem__(self, int(key), value)

    #TODO find a way to do efficient automatic re-indexing
    # can't see that I can do better than Plone though
    # http://developer.plone.org/searching_and_indexing/indexing.html#when-indexing-happens-and-how-to-reindex-manually
    def reindex(self, value):
        self._cat.index_doc(value.key, value)

    # Removal is done with either pop or clear, overriding these methods will
    # control removal.
    def pop(self, key, *args):
        retval = ZopeDict.pop(self, int(key), *args)
        self._cat.unindex_doc(int(key))
        return retval

    def clear(self):
        ZopeDict.clear(self)
        self._cat.clear()

