# ------------------------------------------------------------------------------
# Contact Resources
# ------------------------------------------------------------------------------
from persistent import Persistent
from pyramid.security import Allow
from pyramid.security import Authenticated
from repoze.catalog.indexes.field import CatalogFieldIndex
import transaction
from repoze.catalog.query import Ge

#TODO write my own paginator
import webhelpers.paginate as paginate

from .module import Module

class Contacts(Module):
    __acl__    = [(Allow, Authenticated,   'view'),
                  (Allow, 'group:editors', 'edit')]
    __name__   = 'contacts'

    def __init__(self, parent):
        Module.__init__(self, parent)
        self._cat['name'] = CatalogFieldIndex('name')

class Contact(Persistent):
    __acl__    = [(Allow, Authenticated,   'view'),
                  (Allow, 'group:editors', 'edit')]

    def __init__(self, name, contacts):
        Persistent.__init__(self)
        self.key        = contacts.maxKey() + 1
        self.__parent__ = contacts
        self.__name__   = str(self.key)
        self.name       = name
        contacts[self.key] = self

#---------------------------------------------------------------------------
# Contact Views
#---------------------------------------------------------------------------
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotImplemented
from pyramid.security import authenticated_userid

from wtforms import Form
from wtforms.validators import required
from wtforms.fields import TextField, SubmitField
from wtforms.widgets import SubmitInput

from .name   import chooseName, chooseAddress
from .pagination import Page
from .pagination import CatalogFieldIndexSlicer

class ContactForm(Form):
    name      = TextField(validators=[required()])
    address1  = TextField(u"Street")
    address2  = TextField(u"Suburb")
    city      = TextField()
    postCode  = TextField()
    country   = TextField()
    phone     = TextField()
    email     = TextField()

#TODO mv to new module  formextras?
class SubmitBtn(SubmitInput):
    def __call__(self, field, **kwargs):
        if field.flags.disabled:
            kwargs.setdefault("disabled", True)
        return SubmitInput.__call__(self, field, **kwargs)

class ContactBtns(Form):
    okBtn     = SubmitField(u"OK",       widget=SubmitBtn())
    prevBtn   = SubmitField(u"Previous", widget=SubmitBtn())
    nextBtn   = SubmitField(u"Next",     widget=SubmitBtn())
    cancelBtn = SubmitField(u"Cancel",   widget=SubmitBtn())

class ContactsBtns(Form):
    addBtn    = SubmitField(u"Add Contact")
    delBtn    = SubmitField(u"Delete Contact")
    editBtn   = SubmitField(u"Edit Contact")

@view_config(context=Contacts,
             renderer='templates/contacts.pt',
             permission='view')
def viewContacts(contacts, request):
    btns = ContactsBtns()
    if request.method == 'POST': 
        btns.process(request.POST)
        selection = [ int(selected[7:]) for selected in request.POST
                                        if selected.startswith("select-") ]
        if btns.addBtn.data:
            url = request.resource_url(contacts, "@@add-contact")
            return HTTPFound(location = url)
        elif selection and btns.delBtn.data:
            contacts.delete(selection)
        elif selection and btns.editBtn.data:
            request.session['selectedContacts'] = selection
            contact = contacts.get(selection[0])
            if contact:
                url = request.resource_url(contact, "@@edit")
                return HTTPFound(location = url)
        else:
            return HTTPNotImplemented()
        url = request.resource_url(contacts).rstrip('/')
        return HTTPFound(location = url)

    form = ContactForm()
    headings = [field.label.text for field in form]
    rows = []

    pgParam = request.params.get("page", "1")
    #FIXME do my own pagination
    #page_url = paginate.PageURL_WebOb(request)
    idx = contacts._cat['name']
    #import pdb;pdb.set_trace()
    #XXX hopefully this isn't as bad as it looks
    #docIds = idx.scan_forward(idx.docids())
    #docIds = idx.sort(idx.docids(), CatalogFieldIndex.FWSCAN)
    # it is pretty bad though, so... (abusing encapsulation)
    #docIdList = []
    #for docIds in idx._fwd_index.values():
    #    for docId in docIds:
    #        docIdList.append(docId)
    #docIdList = [ docId for docIds in idx._fwd_index.values() for docId in docIds ]
    # this is still bad

    #numContacts = len(docIdList)
    #page = paginate.Page(docIdList, current_page,
    #                     items_per_page=10, item_count=numContacts,
    #                     url=page_url)
    # print page
    
    #results  = contacts.cat.query(Ge('name', 'Kayla Neville'),
    #                              sort_index='name',
    #                              limit=10)
    #print "found (10 would be good) %d" % results[0]
    #for key in results[1]:
    numContacts = len(contacts)
    #if pgParam == "last":
    #    page = []
    #    numOnLastPage = numContacts % 10
    #    for docIds in reversed(idx._fwd_index.values()):
    #        page[0:0] = docIds # prepend
    #        if len(page) >= numOnLastPage:
    #            page = page[-numOnLastPage:]
    #            break
    #else:
    current_page = int(pgParam)
    #def docIds():
    #    for docIds in idx._fwd_index.values():
    #        for docId in docIds:
    #            yield docId
    posCache = request.session.get('posCache', {})
    slicer = CatalogFieldIndexSlicer(idx, numContacts, posCache)
    page = Page.from_values(slicer, current_page - 1, 10)
    request.session['posCache'] = posCache
    lastPg = (numContacts + 9) / 10

    for key in page:
        contact = contacts.get(key)
        if contact is None: continue
        form.process(obj=contact)
        # TODO use BooleanField?
        checkbox = '<input type="checkbox" '\
                   'name="select-%d" value="" />'% key
        rows.append([checkbox, ]+[field.data for field in form])
    
    return {'btns':        btns,
            'headings':    headings,
            'rows':        rows,
            'numContacts': numContacts,
            'pager':       '<a href="?page=1">1</a> ... '+
                           '<a href="?page=last">last</a> ' +
                           '<a href="?page=%d">%d</a>' % (lastPg, lastPg),
            'currentUser': authenticated_userid(request)}

@view_config(context=Contacts,
             xhr=True,
             renderer="json",
             permission='view')
def getContacts(contacts, request): 
    retval = {}
    return retval
    echo = request.POST.get('sEcho')
    retval['sEcho'] = str(int(echo))
    #contacts = getAppRoot(request).get('contacts')

    numContacts = len(contacts)
    retval['iTotalRecords'] = numContacts
    retval['iTotalDisplayRecords'] = numContacts

    form = ContactForm()
    rows = []
    start  = int(request.POST.get('iDisplayStart'))
    length = int(request.POST.get('iDisplayLength'))
    for name, contact in contacts.items()[start:start+length]:
        form.process(obj=contact)
        checkbox = '<input type="checkbox" '\
                   'name="select-%s" value="" />'% name
        rows.append([checkbox, ]+[field.data for field in form])
        #row = dict(enumerate([field.data for field in form], start=1))
        #row[0] = checkbox
        #row['DT_RowId'] = name
        #rows.append(row)
    retval['aaData'] = rows
    return retval
           

@view_config(name='add-contact',
             context=Contacts,
             renderer='templates/edit_contact.pt',
             permission='edit')
def addContact(contacts, request):
    form = ContactForm()
    btns = ContactBtns()
    retval = {'form':         form,
              'btns':         btns,
              'currentUser':  authenticated_userid(request)}
    if request.method == 'POST':
        form.process(request.POST)
        btns.process(request.POST)
        if btns.cancelBtn.data:
            url = request.resource_url(contacts).rstrip('/')
            return HTTPFound(location = url)
        elif btns.okBtn.data:
            if not form.validate():
                return retval
            # Create a new Contact
            contact = Contact(form.name.data, contacts)
            form.populate_obj(contact)
            url = request.resource_url(contact).rstrip('/')
            return HTTPFound(location = url)
        else:
            return HTTPNotImplemented()

    return retval

@view_config(context=Contact,
             renderer='templates/contact.pt',
             permission='view')
def viewContact(contact, request):
    form = ContactForm(obj=contact)
    return {'form':        form,
            'currentUser': authenticated_userid(request)}

@view_config(name='edit',
             context=Contact,
             renderer='templates/edit_contact.pt',
             permission='edit')
def editContact(contact, request):
    from .app import getAppRoot
    contacts = getAppRoot(request).get('contacts')
    # or contact.__parent__ ?
    form = ContactForm(obj=contact)
    btns = ContactBtns()
    selection = request.session.get('selectedContacts', [])
    myPos = None
    btns.prevBtn.flags.disabled = True
    btns.nextBtn.flags.disabled = True
    try:
        myPos = selection.index(contact.key)
        if myPos > 0:
            btns.prevBtn.flags.disabled = False
        if myPos < len(selection) - 1:
            btns.nextBtn.flags.disabled = False
    except ValueError:
        pass
    retval = {'form':         form,
              'btns':         btns,
              'currentUser':  authenticated_userid(request)}

    if request.method == 'POST':
        form.process(request.POST)
        btns.process(request.POST)
        if btns.cancelBtn.data:
            url = request.resource_url(contact).rstrip('/')
            return HTTPFound(location = url)
        elif btns.okBtn.data:
            request.session['selectedContacts'] = []
            url = request.resource_url(contact).rstrip('/')
        elif btns.prevBtn.data and not btns.prevBtn.flags.disabled:
            selected = selection[myPos - 1]
            url = request.resource_url(contacts, selected, "@@edit")
        elif btns.nextBtn.data and not btns.nextBtn.flags.disabled:
            selected = selection[myPos + 1]
            url = request.resource_url(contacts, selected, "@@edit")
        else:
            return HTTPNotImplemented()

        if not form.validate():
            return retval
        # Update an existing Contact
        form.populate_obj(contact)
        return HTTPFound(location = url)

    return retval

@view_config(name='add-test-data',
             context=Contacts,
             permission='edit')
def addTestData(contacts, request):
    for i in  range(100000):
        contact = Contact(chooseName(), contacts)
        street, district, city = chooseAddress()
        contact.address1 = street
        contact.address2 = district
        contact.city     = city
    return Response('Done!')


