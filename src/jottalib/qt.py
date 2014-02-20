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
import logging

# Part of jottalib. QT4 models. pip install pyqt4

# This is only needed for Python v2 but is harmless for Python v3.
import sip
sip.setapi('QString', 2)

from PyQt4 import QtCore, QtGui

class JFSModel(QtCore.QAbstractListModel):
    
    #Simple models can be created by subclassing this class and implementing
    #the minimum number of required functions. For example, we could implement a
    #simple read-only QStringList-based model that provides a list of strings to
    #a QListView widget. In such a case, we only need to implement the
    #rowCount() function to return the number of items in the list, and the
    #data() function to retrieve items from the list.  Since the model
    #represents a one-dimensional structure, the rowCount() function returns the
    #total number of items in the model. The columnCount() function is
    #implemented for interoperability with all kinds of views, but by default
    #informs views that the model contains only one column.

    def __init__(self, jfs, rootPath, parent=None):
        super(JFSModel, self).__init__(parent)
        self.tree = jfs # a jfstree.JFSTree instance
        self.__currentChildren = [] # a quick cache to avoid too many lookups. Regenerated in .jfsChangePath(), when path is changed
        self.jfsChangePath(rootPath)

    def jfsChangePath(self, newPath):
        self.tree.changePath(newPath)
        self.__currentChildren = list(self.tree.childrenFullPath())

    def rowCount(self, parentidx):
        return len(self.__currentChildren)

    def data(self, idx, role):
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
            path = self.__currentChildren[idx.row()]
        except IndexError:
            print "inxesxxerror: ", idx.row()
            return QtCore.QVariant()

        if role in ( QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole ):
            return QtCore.QVariant(os.path.basename(path))
        elif role == QtCore.Qt.UserRole: # return full path
            return QtCore.QVariant(path)

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
            
    def headerData(self, section, orientation, role):
        #print "headerData", section, orientation, role
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()

    def canFetchMore(self, idx):
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
