# ------------------------------------------------------------------------------
# Module base class
# ------------------------------------------------------------------------------
from zc.dict.dict import Dict as ZopeDict
from repoze.catalog.catalog import Catalog

class Module(ZopeDict):
    def __init__(self, parent):
        ZopeDict.__init__(self)
        self.__parent__  = parent
        parent[self.__name__] = self
        self._cat = Catalog()

    def addIndex(self, idxName):
        print "TODO addIdx"
        pass

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

