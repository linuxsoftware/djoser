# -*- coding: utf-8 -*-
import sys
import os
from os.path import join, dirname

from cgi import FieldStorage
from wtforms import Form
from wtforms.ext.appengine.db import model_form
from wtforms.widgets import html_params, HTMLString
from wtforms.fields import Field, _unset_value
from wtforms.widgets import SubmitInput


#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
class ImageWidget(object):
    """
    Very simple image selection widget
    """
    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        name = "%s.png" % field.name
        url = kwargs.get("url", "%s/%s" % (kwargs.get("path"), name))
        kwargs.setdefault("value", name)
        preview = HTMLString(u"<img %s />" % html_params(name="preview_"+name,
                                                         src=url))
        inputButton = HTMLString(u"<input %s  />" % html_params(name=field.name,
                                                                type=u"file",
                                                                **kwargs))
        return preview + inputButton


class ImageField(Field):
    widget = ImageWidget()

    def process_formdata(self, valuelist):
        if valuelist:
            if isinstance(valuelist[0], FieldStorage):
                data = valuelist[0].value
            else:
                data = valuelist[0]
            if data:
                self.data = db.Blob(data)
        # NB If we reset on no data then a image must always be rechosen
        # so we don't do that

    def _value(self):
        return self.name + ".png"
    

#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
class ImagePreviewWidget(object):
    """
    Super dynamic image selection widget
        ## http://valums.com/ajax-upload/
        ## http://www.zurb.com/playground/ajax_upload
        ## http://ohryan.ca/blog/2011/06/28/how-to-file-upload-progress-bar-no-flash-no-php-addons
    """
    def __call__(self, field, **kwargs):
        return self._body(**kwargs)

    def _head(self):
        return """<script type="text/javascript" src="/static/fileuploader.js"></script>"""

    def _body(self, **kwargs):
        kwargs.setdefault('path', "")
        kwargs.setdefault('name', field.name)
        kwargs.setdefault('width', 100)
        kwargs.setdefault('height', 100)
        kwargs.setdefault('name', field.name)
        body = """
<script type="text/javascript">
  $(function() {
    var button = $('#%(name)sButton');
    var thumb  = $('#%(name)sButton img.thumb');	
    var uploader = new qq.FileUploaderBasic({
      button:   $('#%(name)sButton')[0],
      id:       '%(name)s',
      name:     '%(name)s',
      params:   { 'previewId': '%(path)s/%(name)s.png' },
      action:   '/preview',
      debug:    false,
      multiple: false,
      allowedExtensions: ['png'],
      onSubmit: function(id, fileName) {
        button.addClass('loading');
      },
      onComplete: function(id, fileName, response) {
        thumb.load(function() {
          button.removeClass('loading qq-upload-button-hover qq-upload-button-focus');
          thumb.unbind();
        });
        var previewId = response['previewId'];
        var now = new Date();
        var secsSinceEpoch = Math.floor(now.getTime()/1000);
        $('#%(name)sPreview').val(previewId);
        thumb.attr('src', '/preview/'+secsSinceEpoch+previewId);
      }
    });
    var dz = new qq.UploadDropZone({
      element: button[0],
      onEnter: function(e) {
        button.addClass('qq-upload-drop-area-active');
        e.stopPropagation();
      },
      onLeave: function(e) {
        e.stopPropagation();
      },
      onLeaveNotDescendants: function(e) {
        button.removeClass('qq-upload-drop-area-active');
      },
      onDrop: function(e) {
        button.removeClass('qq-upload-drop-area-active');
        uploader._uploadFile(e.dataTransfer.files[0]);
      }
    });
  });
</script>
<div id="%(name)sButton" class="qq-upload-button"
     style="width: %(width)dpx; height: %(height)dpx;">
  %if field.data:
    <img class="thumb" src="%(path)s/%(name)s.png" />
  %else:
    <img class="thumb" src="/static/empty-%(name)s.png" />
  %endif
</div>
<input id="%(name)sPreview" name="%(name)sPreview" type="hidden" />
<noscript>
  <input id="%(name)s" name="%(name)s" type="file" class="oldSchool" />
</noscript>
        """ % kwargs
        return body

class ImagePreviewField(ImageField):
    widget = ImagePreviewWidget()

    def process(self, formdata, data=_unset_value):
        self.process_errors = []
        if data is _unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default
        try:
            self.process_data(data)
        except ValueError, e:
            self.process_errors.append(e.args[0])

        if formdata:
            try:
                self.raw_data = self._getRawData(formdata)
                self.process_formdata(self.raw_data)
            except ValueError, e:
                self.process_errors.append(e.args[0])

        for filter in self.filters:
            try:
                self.data = filter(self.data)
            except ValueError, e:
                self.process_errors.append(e.args[0])

    def _getRawData(self, formdata):
        if not self.name in formdata:
            return []
        rawData = formdata.getlist(self.name)
        if rawData and rawData[0] != u'':
            return rawData
        return self._getRawPreviewData(formdata)

    def _getRawPreviewData(self, formdata):
        previewName = "%sPreview" % self.name
        if not previewName in formdata:
            return []
        previewData = formdata.getlist(previewName)
        if not previewData:
            return []
        previewId = previewData[0]
        if not previewId:
            return []
        # TODO  FIXME
        memcache = {}
        image = memcache.get(previewId, namespace="ImagePreview")
        if not image:
            return []
        return [ image ]

# FIXME
#
#def postImagePreview(request):
#    if request.method != "POST":
#        raise exc.HTTPMethodNotAllowed()
#    #TODO validation use ImageField?
#    if request.get("qqfile"):
#        image = request.body
#        previewId = request.get('previewId')
#    elif request.POST.get('qqfile'):
#        image = request.POST.get("qqfile").value
#        previewId = request.POST.get('previewId')
#    else:
#        image = ""
#        raise RuntimeError("TODO")
#    if len(image) < memcache.MAX_VALUE_SIZE:
#        # TODO check size in validation
#        timeout = 3600 # 1 hour
#        memcache.set(previewId, image, timeout, namespace="ImagePreview")
#    request.response.headers['Content-Type'] = "text/plain"
#    request.response.out.write("{previewId: '%s'}" % previewId)
#
#
#def getImagePreview(request):
#    if request.method != "GET":
#        raise exc.HTTPMethodNotAllowed()
#    request.path_info_pop() #/preview
#    request.path_info_pop() #/time
#    previewId = request.path_info
#    image = memcache.get(previewId, namespace="ImagePreview")
#    if image:
#        #TODO validation use ImageField?
#        headers = request.response.headers
#        headers["Expires"]        = "Sat, 26 Jul 1997 05:00:00 GMT"
#        headers["Cache-Control"]  = "no-store, no-cache, must-revalidate"
#        headers['Content-Type']   = "image/png"
        request.response.out.write(image)


#---------------------------------------------------------------------------
#---------------------------------------------------------------------------

class SubmitBtn(SubmitInput):
    def __call__(self, field, **kwargs):
        if field.flags.disabled:
            kwargs.setdefault("disabled", True)
        return SubmitInput.__call__(self, field, **kwargs)

