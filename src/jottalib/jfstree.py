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

#stdlib
import os.path
import logging

#jottalib
from . import JFS

class JFSTree(object):
    def __init__(self, username, password, rootpath=None, jailed=False):
        self.rootpath = rootpath is not None and rootpath or '/'
        self.client = JFS.JFS(username, password)
        self.currentpath = self.rootpath
        self.jailed = jailed

    def parent(self):
        node = self.client.getObject(self.currentpath)
        return node.parentPath

    def childrenObjects(self):
        if self.currentpath == '/':
            for d in self.devices():
                yield d
        else:
            p = self.client.getObject(self.currentpath)
            if isinstance(p, JFS.JFSDevice):
                for key, item in p.mountPoints.iteritems():
                    yield item
                    #yield name
            else:    
                for el in itertools.chain(p.folders(), p.files()):
                    #yield el.name
                    yield el

    def children(self):
        return [o.name for o in self.childrenObjects()]

    def changePath(self, newPath):
        if newPath == '..':
            n = self.parent()
            self.currentpath = n.path
            return n
        else:
            if newPath.startswith('./'):
                self.currentpath = self.currentpath + newPath[:1]
            else:
                self.currentpath = newPath

            return self.client.getObject(self.currentpath)

    def devices(self):
        return self.client.devices