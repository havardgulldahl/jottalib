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
import logging, itertools

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

    def columnCount(self): return 1
    def hasChildren(self): return len(self.childNodes) > 0
    def rowCount(self): return len(self.childNodes)
    def pullChildren(self): pass
    def child(self, row, col=0): return self.childNodes[row]

class JFSFileNode(JFSNode):
    def __init__(self, obj, jfs, parent=None):
        super(JFSFileNode, self).__init__(obj, jfs, parent)

class JFSFolderNode(JFSNode):
    def __init__(self, obj, jfs, parent=None):
        super(JFSFolderNode, self).__init__(obj, jfs, parent)

    def pullChildren(self):
    #     self.childNodes = list(self.iterChildren())
    # def iterChildren(self):
    #     'iterate through folders and files'
        for obj in self.obj.folders():
            # yield JFSFolderNode(obj, self.jfs, self)
            self.appendRow(JFSFolderNode(obj, self.jfs, self))
        for obj in self.obj.files():
            # yield JFSFileNode(obj, self.jfs, self)
            self.appendRow(JFSFileNode(obj, self.jfs, self))

class JFSDeviceNode(JFSNode):
    def __init__(self, obj, jfs, parent=None):
        super(JFSDeviceNode, self).__init__(obj, jfs, parent)
        self.childNodes = list([JFSFolderNode(item, self.jfs, self) for item in self.obj.mountPoints.values()])
        #self.appendRows(list([JFSFolderNode(item, self.jfs, self) for item in self.obj.mountPoints.values()]))

class JFSModel(QtGui.QStandardItemModel):

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

    def xrowCount(self, idx):
        item = self.itemFromIndex(idx)
        print 'top item: %s' % item
        return item.rowCount()

    def populateChildNodes(self, idx):
        print 'populateChildNodes %s' % idx
        item = self.itemFromIndex(idx)
        print 'populate item: %s' % item
        item.pullChildren()

    def hasChildren(self, idx): 
        item = self.itemFromIndex(idx)
        if item is not None:
            print 'hasChildren item: %s (%s)' % (item, unicode(item.text()))
        if isinstance(item, JFSFileNode):
            return False
        return True

    def xindex(self, row, column, parent):
        item = self.__currentChildren[row]
        return self.createIndex(row, column, item)


    def xdata(self, idx, role):
        #print "data: ",idx, role
        #The general purpose roles are:
        #Qt::DisplayRole  0 The key data to be rendered (usually text).
        #Qt::DecorationRole 1 The data to be rendered as a decoration (usually an icon).
        #Qt::EditRole 2 The data in a form suitable for editing in an editor.
        #Qt::ToolTipRole  3 The data displayed in the item's tooltip.
        #Qt::StatusTipRole  4 The data displayed in the status bar.
        #Qt::WhatsThisRole  5 The data displayed for the item in "What's This?" mode.
        #Qt::SizeHintRole 13  The size hint for the item that will be supplied to views.

        #Roles describing appearance and meta data:
        #Qt::FontRole 6 The font used for items rendered with the default delegate.
        #Qt::TextAlignmentRole  7 The alignment of the text for items rendered with the default delegate.
        #Qt::BackgroundRole 8 The background brush used for items rendered with the default delegate.
        #Qt::BackgroundColorRole  8 This role is obsolete. Use BackgroundRole instead.
        #Qt::ForegroundRole 9 The foreground brush (text color, typically) used for items rendered with the default delegate.
        #Qt::TextColorRole  9 This role is obsolete. Use ForegroundRole instead.
        #Qt::CheckStateRole 10  This role is used to obtain the checked state of an item (see Qt::CheckState).

        #Accessibility roles:
        #Qt::AccessibleTextRole 11  The text to be used by accessibility extensions and plugins, such as screen readers.
        #Qt::AccessibleDescriptionRole  12  A description of the item for accessibility purposes.

        #User roles:
        #Qt::UserRole 32  The first role that can be used for application-specific purposes.

        if not idx.isValid():
            return QtCore.QVariant()

        #print "idxrow: ", idx.row()
        try:
            item = self.__currentChildren[idx.row()]
            # print repr(item)
        except IndexError:
            print "inxesxxerror: ", idx.row()
            return QtCore.QVariant()

        if role in ( QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole ):
            return QtCore.QVariant(item.name)
        elif role == QtCore.Qt.UserRole: # return full path
            return QtCore.QVariant(item.path)

        #elif role == QtCore.Qt.DecorationRole:
            # coverPix = QtGui.QPixmap()
            # coverPix.loadFromData(album['cover'])
            # return coverPix.scaled(200,200, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        # elif role == QtCore.Qt.SizeHintRole:
        #     return QtCore.QSize(200,200)
        # elif role == QtCore.Qt.TextAlignmentRole:
        #     return QtCore.Qt.AlignCenter
        #elif role == QtCore.Qt.TextColorRole:
            #return QtGui.QColor(255,255,255,177)
        else:
            return QtCore.QVariant()
            
    def xheaderData(self, section, orientation, role):
        #print "headerData", section, orientation, role
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()

    def xcanFetchMore(self, idx):
        return False

    def fxetchMore(self, parentidx):
        #print "fetchmore: ", parentidx
        self.layoutAboutToBeChanged.emit()
        self.albums = list(itertools.chain.from_iterable([self.albums, loadAlbums(len(self.albums), 15)]))
        self.layoutChanged.emit()
        #print "albums;: ", self.albums
        self.dataHasntBeenFetched = False




if __name__ == '__main__':
    print dir()
