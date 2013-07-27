from itertools import islice
import math
import numbers

class Page(object):
    size = 10

    def __init__(self, iterator, index, length):
        self._iterator = iterator
        self.index = index
        self.pages = int(math.ceil(float(length)/self.size))

    def __iter__(self):
        return self._iterator

    @classmethod
    def from_values(cls, values, index, length):
        # values must be sliceable
        start = index * cls.size
        stop = (index + 1) * cls.size
        iterator = iter(values[start:stop])
        return Page(iterator, index, length)

    @classmethod
    def from_iter(cls, iterator, index, length):
        start = index * cls.size
        stop = (index + 1) * cls.size
        slice = islice(iterator, start, stop)
        return Page(slice, index, length)


class BTreeSlicer(object):
    """
    """
    def __init__(self, tree, length):
        self.tree   = tree
        self.length = length

    def __getitem__(self, items):
        return self.tree[items]

    def __len__(self):
        return self.length


class CatalogFieldIndexSlicer(object):
    """
    The goal of this class is to quickly pull out a slice of doc_ids 
    from a repoze.catalog FieldIndex in the order of the indexed field.  

    I break encapsulation and use the _fwd_index member.  This is an 
    OOBTree which maps the field to a OOBTreeSets which contains 1 or
    more (maybe 0 even?) doc_ids.  This is via OOBTreeItems.  There is
    reasonable performance for array indexing, but as I don't know how
    many doc_ids in each tree set I need to iterate each OOBTreeSet and 
    then get its length.  This is a bit slow.  But I can iterate either 
    forwards or backwards, which is the first optimization this class
    has.  The other optimization is if given a cache it will store the 
    current index in the OOBTreeItems with the number of doc_ids before 
    that index, this can be used to save having to calculate the length 
    of the OOBTreeSets before the index (if going forwards), or after
    the index (if reversing).  These optimizations should make it fast
    to go to either end of the data, or to step forwards or backwards
    in smallish steps.
    """
    def __init__(self, index, length, posCache=None):
        self.index    = index
        self.length   = length
        if posCache is None:
            self.posCache = {}
        else:
            self.posCache = posCache
        self.posCache.setdefault('index',  0)
        self.posCache.setdefault('offset', 0)

    def __getitem__(self, items):
        if isinstance(items, numbers.Integral):
            if items < 0 or items >= self.length:
                raise IndexError("out of range")
            start = items
            stop  = items + 1
        else:
            start, stop, stride = items.indices(self.length)
            if stride != 1:
                raise Exception("stride != 1, not supported")

        offset = self.posCache['offset']
        if start < 50:
            retval = self.getItemsFromStart(start, stop)
        elif stop > self.length - 50:
            retval = self.getItemsFromEnd(start, stop)
        elif offset <= start < offset + 100:
            retval = self.getItemsForwardsFromCurrent(start, stop)
        elif offset - 100 < stop <= offset:
            retval = self.getItemsBackwardsFromCurrent(start, stop)
        elif start < (self.length / 2):
            retval = self.getItemsFromStart(start, stop)
        else:
            retval = self.getItemsFromEnd(start, stop)

        if isinstance(items, numbers.Integral):
            retval = retval[0]
        return retval

    def getItemsForwardsFromCurrent(self, start, stop):
        # double check in range before calling __getItemsForwards
        if start >= self.posCache['offset']:
            return self.__getItemsForwards(start, stop)
        else:
            return self.getItemsFromStart(start, stop)

    def getItemsFromStart(self, start, stop):
        self.posCache['index']  = 0
        self.posCache['offset'] = 0
        return self.__getItemsForwards(start, stop)

    def __getItemsForwards(self, start, stop):
        retval = []
        numNeeded = stop - start
        fwdi = iter(self.index._fwd_index.values())
        fwdi = islice(fwdi, self.posCache['index'], None)
        offset = self.posCache['offset']
        start -= offset
        stop  -= offset
        while len(retval) < numNeeded:
            values = next(fwdi)
            numValues = len(values)
            self.posCache['index']  += 1
            self.posCache['offset'] += numValues
            if start < numValues:
                retval.extend(islice(values, start, stop))
                start = 0
            else:
                start -= numValues
            stop -= numValues
        return retval

    def getItemsBackwardsFromCurrent(self, start, stop):
        # double check in range before calling __getItemsBackwards
        # this check is a bit more paranoid than it needs to be,
        # but it makes the calculation simpler
        if stop <= self.posCache['offset']:
            return self.__getItemsBackwards(start, stop)
        else:
            return self.getItemsFromEnd(start, stop)

    def getItemsFromEnd(self, start, stop):
        self.posCache['index']  = len(self.index._fwd_index)
        self.posCache['offset'] = self.length
        return self.__getItemsBackwards(start, stop)

    def __getItemsBackwards(self, start, stop):
        retval = []
        numNeeded = stop - start
        valuesStart = self.posCache['offset']
        fwdri = reversed(self.index._fwd_index.values())
        rindex = len(self.index._fwd_index) - self.posCache['index']
        fwdri = islice(fwdri, rindex, None)
        while len(retval) < numNeeded:
            values = next(fwdri)
            numValues = len(values)
            valuesStart -= numValues
            self.posCache['index'] -= 1
            self.posCache['offset'] = valuesStart
            if stop > valuesStart:
                if start >= valuesStart:
                    retval[0:0] = list(islice(values,
                                              start - valuesStart,
                                              stop  - valuesStart))
                else:
                    retval[0:0] = list(islice(values, 
                                              0,
                                              stop - valuesStart))
        return retval

    def __len__(self):
        return self.length

