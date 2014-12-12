#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''Mount your JottaCloud files locally and use it with your normal file tools'''
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
import sys, os, pwd, stat, errno, netrc
import urllib, logging, datetime, argparse
import time
import itertools
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


# import jotta
from jottalib import JFS, __version__

# import dependenceis (get them with pip!)
try:
    from fuse import FUSE, Operations, LoggingMixIn # this is 'pip install fusepy'
except ImportError:
    print "JottaFuse won't work without fusepy! Please run `pip install fusepy`."
    raise

class JottaFuseError(OSError):
    pass

ESUCCESS=0

BLACKLISTED_FILENAMES = ('.hidden', '._', '.DS_Store', '.Trash', '.Spotlight-', '.hotfiles-btree',
                         'lost+found', 'Backups.backupdb', 'mach_kernel')

def is_blacklisted(path):
    _basename = os.path.basename(path)
    for bf in BLACKLISTED_FILENAMES:
        if _basename.startswith(bf):
            return True
    return False

class JottaFuse(LoggingMixIn, Operations):
    '''
    A simple filesystem for JottaCloud.

    '''

    def __init__(self, username, password, path='.'):
        self.client = JFS.JFS(username, password)
        self.root = path
        self.dirty = False # True if some method has changed/added something and we need to get fresh data from JottaCloud
        # TODO: make self.dirty more smart, to know what path, to get from cache and not
        self.__newfiles = []
        self.__newfolders = []

    def _getpath(self, path):
        "A wrapper of JFS.getObject(), with some tweaks that make sense in a file system."
        if is_blacklisted(path):
            raise JottaFuseError('Blacklisted file, refusing to retrieve it')

        return self.client.getObject(path, usecache=self.dirty is not True)

    # def access(self, path, mode):
    #     '''Use the real uid/gid to test for access to path.

    #     mode should be F_OK to test the existence of path, or it can be the inclusive OR of
    #     one or more of R_OK, W_OK, and X_OK to test permissions. Return True if access is allowed,
    #     False if not. See the Unix man page access(2) for more information.
    #     '''
    #     if mode & os.X_OK:

    def create(self, path, mode):
        if is_blacklisted(path):
            raise JottaFuseError('Blacklisted file')
        if not path in self.__newfiles:
            self.__newfiles.append(path)
        return self.__newfiles.index(path)
        return ESUCCESS

    def chmod(self, path, mode):
        '''.chmod makes no sense here, always return success (0)'''
        return ESUCCESS

    def chown(self, path, uid, gid):
        '''.chown makes no sense here, always return success (0)'''
        return ESUCCESS

    def destroy(self, path):
        #do proper teardown
        pass

    def getattr(self, path, fh=None):
        pw = pwd.getpwuid( os.getuid() )
        if path in self.__newfolders: # folder was just created, not synced yet
            return {
                'st_atime': time.time(),
                'st_gid': pw.pw_gid,
                'st_mode': stat.S_IFDIR | 0755,
                'st_mtime': time.time(),
                'st_size': 0,
                'st_uid': pw.pw_uid,
                }
        elif path in self.__newfiles: # file was just created, not synced yet
            return {
                'st_atime': time.time(),
                'st_gid': pw.pw_gid,
                'st_mode': stat.S_IFREG | 0644,
                'st_mtime': time.time(),
                'st_size': 0,
                'st_uid': pw.pw_uid,
                }
        try:
            f = self._getpath(path)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '') # can't help you
        if isinstance(f, (JFS.JFSFile, JFS.JFSFolder)) and f.is_deleted():
            raise OSError(errno.ENOENT)

        if isinstance(f, JFS.JFSFile):
            _mode = stat.S_IFREG | 0644
        elif isinstance(f, JFS.JFSFolder):
            _mode = stat.S_IFDIR | 0755
        elif isinstance(f, (JFS.JFSMountPoint, JFS.JFSDevice) ):
            _mode = stat.S_IFDIR | 0555 # these are special jottacloud dirs, make them read only
        else:
            logging.warning('Unknown jfs object: %s <-> "%s"' % (type(f), f.tag) )
            _mode = stat.S_IFDIR | 0555
        return {
                'st_atime': isinstance(f, JFS.JFSFile) and time.mktime(f.updated.timetuple()) or time.time(),
                'st_gid': pw.pw_gid,
                'st_mode': _mode,
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
        if not isinstance(f, JFS.JFSFolder):
            raise OSError(errno.EACCES) # can only create stuff in folders
        if isinstance(f, (JFS.JFSFile, JFS.JFSFolder)) and f.is_deleted():
            raise OSError(errno.ENOENT)
        r = f.mkdir(newfolder)
        self.dirty = True
        self.__newfolders.append(path)
        return ESUCCESS

    def read(self, path, size, offset, fh):
        if path in self.__newfiles: # file was just created, not synced yet
            return ''
        try:
            f = self._getpath(path)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        if isinstance(f, (JFS.JFSFile, JFS.JFSFolder)) and f.is_deleted():
            raise OSError(errno.ENOENT)
        data = StringIO(f.read())
        data.seek(offset, 0)
        buf = data.read(size)
        data.close()
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


    def rename(self, old, new):
        if old == new: return
        try:
            f = self._getpath(old)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        f.rename(new)
        return ESUCCESS

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

    def truncate(self, path, length, fh=None):
        "Download existing path, truncate and reupload"
        if path in self.__newfiles: # file was just created, not synced yet
            return ''
        try:
            f = self._getpath(path)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        if isinstance(f, (JFS.JFSFile, JFS.JFSFolder)) and f.is_deleted():
            raise OSError(errno.ENOENT)
        data = StringIO(f.read())
        data.truncate(length)
        try:
            self.client.up(path, data) # replace file contents
            return ESUCCESS
        except:
            raise
            raise OSError(errno.ENOENT, '')


    def unlink(self, path):
        if path in self.__newfolders: # folder was just created, not synced yet
            self.__newfolders.remove(path)
            return
        elif path in self.__newfiles: # file was just created, not synced yet
            self.__newfiles.remove(path)
            return
        try:
            f = self._getpath(path)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        r = f.delete()
        self.dirty = True
        return ESUCCESS

    rmdir = unlink # alias

    def write(self, path, data, offset, fh):
        if is_blacklisted(path):
            raise JottaFuseError('Blacklisted file')

        if path in self.__newfiles: # file was just created, not synced yet
            print "__newfiles path: %s" % path
            f = self.client.up(path, StringIO(data))
            self.__newfiles.remove(path)
            return len(data)
        try:
            f = self._getpath(path)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        olddata = f.read()
        newdata = olddata[:offset] + data
        f.write(newdata)
        return len(data)


if __name__ == '__main__':
    def is_dir(path):
        if not os.path.isdir(path):
            raise argparse.ArgumentTypeError('%s is not a valid directory' % path)
        return path
    parser = argparse.ArgumentParser(description=__doc__,
                                     epilog="""The program expects to find an entry for "jottacloud" in your .netrc,
                                     or JOTTACLOUD_USERNAME and JOTTACLOUD_PASSWORD in the running environment.
                                     This is not an official JottaCloud project.""")
    parser.add_argument('--debug', action='store_true', help='Add a lot of messages to help debug')
    parser.add_argument('--debug-http', action='store_true', help='Show all HTTP traffic')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('mountpoint', type=is_dir, help='A path to an existing directory where you want your JottaCloud tree mounted')
    args = parser.parse_args()
    if args.debug_http:
        import httplib
        httplib.HTTPConnection.debuglevel = 1
    if args.debug:
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    try:
        n = netrc.netrc()
        username, account, password = n.authenticators('jottacloud') # read .netrc entry for 'machine jottacloud'
    except:
        username = os.environ['JOTTACLOUD_USERNAME']
        password = os.environ['JOTTACLOUD_PASSWORD']

    fuse = FUSE(JottaFuse(username, password), args.mountpoint, foreground=True, nothreads=args.debug)


