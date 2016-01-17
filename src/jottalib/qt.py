# -*- encoding: utf-8 -*-
#
# This file is part of jottafs.
#
# jottafs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# jottafs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with jottafs.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2011,2013,2014 Håvard Gulldahl <havard@gulldahl.no>

# stdlib
import os.path
import logging, itertools, tempfile

logging.getLogger(__name__)

# Part of jottalib.
import jottalib.JFS as JFS

# This is only needed for Python v2 but is harmless for Python v3.
import sip
sip.setapi('QString', 2)

from PyQt4 import QtCore, QtGui

class JFSNode(QtGui.QStandardItem):
    def __init__(self, obj, jfs, parent=None):
        super(JFSNode, self).__init__(parent)
        self.obj = obj
        self.setText(obj.name)
        self.jfs = jfs
        self.childNodes = []

    def flags(self):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
    def columnCount(self): return 1
    def hasChildren(self): return len(self.childNodes) > 0
    def rowCount(self): return len(self.childNodes)
    def pullChildren(self): pass
    def child(self, row, col=0): return self.childNodes[row]

class JFSFileNode(JFSNode):
    def __init__(self, obj, jfs, parent=None):
        super(JFSFileNode, self).__init__(obj, jfs, parent)
        self.isUploading = False # a flag that is True when the file is currently uploadign

    def flags(self):
        if self.isUploading:
            return QtCore.Qt.NoItemFlags
        elif self.obj.is_deleted():
            return QtCore.Qt.NoItemFlags
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled

class JFSFolderNode(JFSNode):
    def __init__(self, obj, jfs, parent=None):
        super(JFSFolderNode, self).__init__(obj, jfs, parent)
        self.childrenAlreadyPulled = False

    def flags(self):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled

    def pullChildren(self, hideDeleted=True):
        if self.childrenAlreadyPulled: return
        for obj in self.obj.folders():
            if hideDeleted and obj.is_deleted(): continue
            self.appendRow(JFSFolderNode(obj, self.jfs, self))
        for obj in self.obj.files():
            if hideDeleted and obj.is_deleted(): continue
            self.appendRow(JFSFileNode(obj, self.jfs, self))
        self.childrenAlreadyPulled = True

class JFSDeviceNode(JFSNode):
    def __init__(self, obj, jfs, parent=None):
        super(JFSDeviceNode, self).__init__(obj, jfs, parent)
        self.childNodes = list([JFSFolderNode(item, self.jfs, self) for item in self.obj.mountPoints.values()])

class JFSModel(QtGui.QStandardItemModel):
    tempfileCreated = QtCore.pyqtSignal(unicode)
    uploadFile = QtCore.pyqtSignal(unicode, unicode) # (local file path, remote folder path)

    def __init__(self, jfs, rootPath, parent=None):
        super(JFSModel, self).__init__(parent)
        self.jfs = jfs # a jottalib.JFS.JFS instance
        self.rootItem = self.invisibleRootItem() # top item
        self.rootPath = rootPath
        rawObj = self.jfs.getObject(self.rootPath)
        if isinstance(rawObj, JFS.JFSDevice):
            self.rootObject = JFSDeviceNode(rawObj, jfs)
        elif isinstance(rawObj, (JFS.JFSMountPoint, JFS.JFSFolder)):
            self.rootObject = JFSFolderNode(rawObj, jfs)
        elif isinstance(rawObj, JFS.JFSFile):
            self.rootObject = JFSFileNode(rawObj, jfs)
        self.rootItem.appendRows(self.rootObject.childNodes)
        self.uploadFile.connect(self.upload)

    def upload(self, localpath, remotefolder):
        log.debug('upload %s -> %s', localpath, remotefolder)
        self.jfs.up(remotefolder, open(localpath, 'rb'))

    def populateChildNodes(self, idx):
        log.debug('populateChildNodes %s', idx)
        if self.hasChildren(idx):
            self.itemFromIndex(idx).pullChildren()

    def hasChildren(self, idx):
        item = self.itemFromIndex(idx)
        # if item is not None:
        #     log.debug('hasChildren item: %s (%s)', item, unicode(item.text()))
        if isinstance(item, JFSFileNode):
            return False
        return True

    def flags(self, idx):
        item = self.itemFromIndex(idx)
        if item is not None: return item.flags()

    def mimeData(self, idxes):
        item = self.itemFromIndex(idxes.pop())
        if item is None:
            return
        log.debug('mimeData item: %s (%s)', item, unicode(item.text()))

        md = jottaMimeData()
        data = item.obj.read()
        md.dataRequested.connect(lambda mt: self.createData(mt, data))
        self.tempfileCreated.connect(lambda fn: md.setTempfile(fn))
        md.setData(item.obj.mime, data)
        if item.obj.is_image():
            img = QtGui.QImage(item.obj.name)
            img.loadFromData(data)
            md.setImageData(img)
        return md

    def createData(self, mimeType, data):
      #if not mimeType.split('/')[0] in ('image', ):
      #    return
      print "createData", mimeType
      with tempfile.NamedTemporaryFile(delete=False) as f:
          f.write(data)
          print f.name
          self.tempfileCreated.emit(f.name)

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction

    def dropMimeData(self, mimedata, action, row, column, parent):
        log.debug("dropMimeData %s (parent %s)", action, parent)
        log.debug("dropped: %s", mimedata.formats())
        if action == QtCore.Qt.CopyAction:
            # put this data on jottacloud
            log.debug("upload data")

            return True
        return False

class jottaMimeData(QtCore.QMimeData):
    dataRequested = QtCore.pyqtSignal(unicode)

    def retrieveData(self, mimeType, _type):
      print "retrieveData", mimeType, _type
      self.dataRequested.emit(mimeType)
      return super(jottaMimeData, self).retrieveData(mimeType, _type)

    def setTempfile(self, fn):
      print "setTempfile", fn
      self.setUrls([QtCore.QUrl(fn), ])
