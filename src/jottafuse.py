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
# Copyright 2011,2013,2014 Håvard Gulldahl <havard@gulldahl.no>

# metadata

__author__ = 'havard@gulldahl.no'

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
from fuse import FUSE, Operations, LoggingMixIn # this is 'pip install fusepy'

class JottaFuseError(JFS.JFSError):
    pass

class JottaFuse(LoggingMixIn, Operations):
    '''
    A simple filesystem for JottaCloud.

    '''

    def __init__(self, username, password, path='.'):
        self.client = JFS.JFS(username, password)
        self.root = path
        self.dirty = False # True if some method has changed/added something and we need to get fresh data from JottaCloud
        # TODO: make self.dirty more smart, to know what path, to get from cache and not

    def _getpath(self, path):
        "A wrapper of JFS.getObject(), with some tweaks that make sense in a file system."
        BLACKLISTED_FILENAMES = ('.hidden', '._', '.DS_Store', '.Trash', '.Spotlight-', '.hotfiles-btree',
                                 'lost+found', 'Backups.backupdb')
        _basename = os.path.basename(path)
        for bf in BLACKLISTED_FILENAMES:
            if _basename.startswith(bf):
                raise JottaFuseError('Blacklisted file, refusing to retrieve it')

        return self.client.getObject(path, usecache=self.dirty is not True)

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
            f = self._getpath(path)
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

    def mkdir(self, path, mode):
        parentfolder = os.path.dirname(path)
        newfolder = os.path.basename(path)
        try:
            f = self._getpath(parentfolder)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        r = f.mkdir(newfolder)
        self.dirty = True

    def read(self, path, size, offset, fh):
        try:
            f = StringIO(self._getpath(path).read())
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
            p = self._getpath(path)
            if isinstance(p, JFS.JFSDevice):
                for name in p.mountPoints.keys():
                    yield name
            else:    
                for el in itertools.chain(p.folders(), p.files()):
                    if not el.is_deleted():
                        yield el.name

    def statfs(self, path):
        "Return a statvfs(3) structure, for stat and df and friends"
        # from fuse.py source code:
        # 
        # class c_statvfs(Structure):
        # _fields_ = [
        # ('f_bsize', c_ulong), # preferred size of file blocks, in bytes
        # ('f_frsize', c_ulong), # fundamental size of file blcoks, in bytes
        # ('f_blocks', c_fsblkcnt_t), # total number of blocks in the filesystem
        # ('f_bfree', c_fsblkcnt_t), # number of free blocks
        # ('f_bavail', c_fsblkcnt_t), # free blocks avail to non-superuser
        # ('f_files', c_fsfilcnt_t), # total file nodes in file system
        # ('f_ffree', c_fsfilcnt_t), # free file nodes in fs
        # ('f_favail', c_fsfilcnt_t)] # 
        #
        # On Mac OS X f_bsize and f_frsize must be a power of 2
        # (minimum 512).

        _blocksize = 512
        _usage = self.client.usage
        _fs_size = self.client.capacity 
        if _fs_size == -1: # unlimited
            # Since backend is supposed to be unlimited, 
            # always return a half-full filesystem, but at least 1 TB)
            _fs_size = max(2 * _usage, 1024 ** 4)
        _bfree = ( _fs_size - _usage ) // _blocksize
        return {
            'f_bsize': _blocksize, 
            'f_frsize': _blocksize,
            'f_blocks': _fs_size // _blocksize,
            'f_bfree': _bfree,
            'f_bavail': _bfree,
            # 'f_files': c_fsfilcnt_t,
            # 'f_ffree': c_fsfilcnt_t,
            # 'f_favail': c_fsfilcnt_t

        }


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


