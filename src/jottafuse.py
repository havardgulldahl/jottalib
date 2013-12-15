#!/usr/bin/env python
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
# Copyright 2011,2013 Håvard Gulldahl <havard@gulldahl.no>

# metadata

__author__ = 'havard@gulldahl.no'
__version__ = '0.1'

# importing stdlib
import sys, os, pwd, stat, errno
import urllib, logging, datetime
import time
import itertools
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


# import jotta
from jottalib import JFS

# import dependenceis (get them with pip!)
from fuse import FUSE, Operations, LoggingMixIn # this is 'fusepy'

class JottaFuse(LoggingMixIn, Operations):
    '''
    A simple filesystem for JottaCloud.

    '''

    def __init__(self, username, password, path='.'):
        self.client = JFS.JFS(username, password)
        self.root = path

    def xx_create(self, path, mode):
        f = self.sftp.open(path, 'w')
        f.chmod(mode)
        f.close()
        return 0

    def destroy(self, path):
        #self.client.close()
        pass

    def getattr(self, path, fh=None):
        try:
            f = self.client.getObject(path)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        pw = pwd.getpwuid( os.getuid() )
        return {
                'st_atime': isinstance(f, JFS.JFSFile) and time.mktime(f.updated.timetuple()) or time.time(),
                'st_gid': pw.pw_gid,
                'st_mode': isinstance(f, JFS.JFSFile) and (stat.S_IFREG | 0444)  or (stat.S_IFDIR | 0755), 
                'st_mtime': isinstance(f, JFS.JFSFile) and time.mktime(f.modified.timetuple()) or time.time(),
                'st_size': isinstance(f, JFS.JFSFile) and f.size  or 0,
                'st_uid': pw.pw_uid,
                }

    def xx_mkdir(self, path, mode):
        return self.sftp.mkdir(path, mode)

    def read(self, path, size, offset, fh):
        try:
            f = StringIO(self.client.getObject(path).read())
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        f.seek(offset, 0)
        buf = f.read(size)
        f.close()
        return buf

    def readdir(self, path, fh):
        yield '.'
        yield '..'
        if path == '/':
            for d in self.client.devices:
                yield d.name
        else:
            p = self.client.getObject(path)
            if isinstance(p, JFS.JFSDevice):
                for name in p.mountPoints.keys():
                    yield name
            else:    
                for el in itertools.chain(p.folders(), p.files()):
                    yield el.name

    def xx_rename(self, old, new):
        return self.sftp.rename(old, self.root + new)

    def xx_rmdir(self, path):
        return self.sftp.rmdir(path)

    def xx_unlink(self, path):
        return self.sftp.unlink(path)

    def xx_write(self, path, data, offset, fh):
        f = self.sftp.open(path, 'r+')
        f.seek(offset, 0)
        f.write(data)
        f.close()
        return len(data)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: %s <mountpoint>' % sys.argv[0])
        sys.exit(1)

    fuse = FUSE(JottaFuse(username=os.environ['JOTTACLOUD_USERNAME'], password=os.environ['JOTTACLOUD_PASSWORD']), 
                sys.argv[1], foreground=True, nothreads=True)


