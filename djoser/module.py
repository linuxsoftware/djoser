# ------------------------------------------------------------------------------
# Module base class
# ------------------------------------------------------------------------------
from zc.dict.dict import Dict as ZopeDict
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex

class Module(ZopeDict):
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
        return self._cat[self._currentIndex]

    def delete(self, names):
        print "TODO delete"
        pass

    def maxKey(self):
        return self._data.maxKey() if len(self) else 0

    # zc.dict interface
    # Addition is done with __setitem__, overriding it will control addition.
    def __setitem__(self, key, value):
        self._cat.index_doc(key, value)
        ZopeDict.__setitem__(self, key, value)

    # Removal is done with either pop or clear, overriding these methods will
    # control removal.
    def pop(self, key, *args):
        retval = ZopeDict.pop(self, key, *args)
        self._cat.unindex_doc(key)
        return retval

    def clear(self):
        ZopeDict.clear(self)
        self._cat.clear()

