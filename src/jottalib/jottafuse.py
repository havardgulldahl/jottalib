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
# Copyright 2011,2013-2015 Håvard Gulldahl <havard@gulldahl.no>

# metadata

__author__ = 'havard@gulldahl.no'

# importing stdlib
import sys, os, pwd, stat, errno
import urllib, logging, datetime, argparse
import time
import itertools
try:
    from cStringIO import StringIO # py2
except ImportError:
    from io import StringIO # py3

logging.captureWarnings(True)
log = logging.getLogger(__name__)

# import jotta
from jottalib import JFS, __version__
from jottalib.contrib.mwt import Memoize

# import dependenceis (get them with pip!)
try:
    from fuse import FUSE, Operations, LoggingMixIn, FuseOSError # this is 'pip install fusepy'
except ImportError:
    print "JottaFuse won't work without fusepy! Please run `pip install fusepy`."
    raise

class JottaFuseError(FuseOSError):
    pass


ESUCCESS=0

BLACKLISTED_FILENAMES = ('.hidden', '._', '._.', '.DS_Store',
                         '.Trash', '.Spotlight-', '.hotfiles-btree',
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


    def __init__(self, auth, path='.'):
        self.client = JFS.JFS(auth)
        self.__newfiles = {} # a dict of stringio objects
        self.__newfolders = []
        self.ino = 0

    #
    # setup and teardown
    #
    def init(self, rootpath):
        # Called on filesystem initialization. (Path is always /)
        # Use it instead of __init__ if you start threads on initialization.
        #TODO: Set up threaded work queue
        pass

    def destroy(self, path):
        #TODO: do proper teardown
        pass


    #
    # helpers
    #

    def _getpath(self, path):
        "A wrapper of JFS.getObject(), with some tweaks that make sense in a file system."
        if is_blacklisted(path):
            raise JottaFuseError('Blacklisted file, refusing to retrieve it')

        return self.client.getObject(path)

    def _dirty(self, path):
        'Remove path from cache'
        return Memoize().yank_path(path)

    #
    # some methods are expected to always work on a rw filesystem, so let's make them work
    #

    def _success(self, *args):
        '''shortcut to always return success (0) to masquerade as a proper filesystem'''
        return 0


    chmod = _success
    chown = _success
    utimens = _success
    setxattr = _success


    #
    # fuse syscall implementations
    #


    def create(self, path, mode, fi=None):
        if is_blacklisted(path):
            raise JottaFuseError('Blacklisted file')
        self.__newfiles[path] = StringIO()
        self.ino += 1
        return self.ino

    @Memoize(timeout=60) # remember every result for 60 seconds
    def getattr(self, path, fh=None):
        if is_blacklisted(path):
            raise OSError(errno.ENOENT)
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
            raise OSError(errno.ENOENT, '') # file not found
        if isinstance(f, (JFS.JFSFile, JFS.JFSFolder, JFS.JFSIncompleteFile)) and f.is_deleted():
            raise OSError(errno.ENOENT)

        if isinstance(f, (JFS.JFSIncompleteFile, JFS.JFSFile)):
            _mode = stat.S_IFREG | 0644
        elif isinstance(f, JFS.JFSFolder):
            _mode = stat.S_IFDIR | 0755
        elif isinstance(f, (JFS.JFSMountPoint, JFS.JFSDevice) ):
            _mode = stat.S_IFDIR | 0555 # these are special jottacloud dirs, make them read only
        else:
            if not f.tag in ('user', ):
                log.warning('Unknown jfs object: %s <-> "%s"' % (type(f), f.tag) )
            _mode = stat.S_IFDIR | 0555
        return {
                'st_atime': time.mktime(f.modified.timetuple()) if isinstance(f, JFS.JFSFile) else time.time(),
                'st_gid': pw.pw_gid,
                'st_mode': _mode,
                'st_mtime': time.mktime(f.modified.timetuple()) if isinstance(f, JFS.JFSFile) else time.time(),
                'st_size': f.size if isinstance(f, JFS.JFSFile) else 0,
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
        self.__newfolders.append(path)
        self._dirty(path)
        return ESUCCESS

    def open(self, path, flags):
        if flags & os.O_WRONLY:
            if not self.__newfiles.has_key(path):
                self.__newfiles[path] = StringIO()
            self.ino += 1
            return self.ino
        return super(JottaFuse, self).open(path, flags)

    def read(self, path, size, offset, fh):
        if path in self.__newfiles.keys(): # file was just created, not synced yet
            data = StringIO(self.__newfiles[path].getvalue())
            data.seek(offset, 0)
            buf = data.read(size)
            data.close()
            return buf
        else:
            try:
                f = self._getpath(path)
            except JFS.JFSError:
                raise OSError(errno.ENOENT, '')
            if isinstance(f, (JFS.JFSFile, JFS.JFSFolder)) and f.is_deleted():
                raise OSError(errno.ENOENT)
            # gnu tools may happily ask for content beyond file size
            # but jottacloud doesn't like that
            # so we make sure we stay within file size (f.size)
            end = min(offset+size, f.size)
            log.debug("f.readpartial(%s, %s) on file of size %s" % (offset, end, f.size))
            return f.readpartial(offset, end)

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

    def release(self, path, fh):
        "Run after a read or write operation has finished. This is where we upload on writes"
        #print "release! inpath:", path in self.__newfiles.keys()
        # if the path exists in self.__newfiles.keys(), we have a new version to upload
        try:
            f = self.__newfiles[path] # make a local shortcut to Stringio object
            f.seek(0, os.SEEK_END)
            if f.tell() > 0: # file has length
                self.client.up(path, f) # upload to jottacloud
            del self.__newfiles[path]
            del f
            self._dirty(path)
        except KeyError:
            pass
        return ESUCCESS

    def rename(self, old, new):
        if old == new: return
        try:
            f = self._getpath(old)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        f.rename(new)
        self._dirty(old)
        self._dirty(new)
        return ESUCCESS

    @Memoize(timeout=60)
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

    def symlink(self, linkname, existing_file):
        """Called to create a symlink `target -> source` (e.g. ln -s existing_file linkname). In jottafuse, we upload the _contents_ of source.

        This is a handy shortcut for streaming uploads directly from disk, without reading the file
        into memory first"""
        log.info("***SYMLINK* %s (link) -> %s (existing)", linkname, existing_file)
        sourcepath = os.path.abspath(existing_file)
        if not os.path.exists(sourcepath): # broken symlink
            raise OSError(errno.ENOENT, '')
        try:
            with open(sourcepath) as sourcefile:
                self.client.up(linkname, sourcefile)
                return ESUCCESS
        except Exception as e:
            log.exception(e)

        raise OSError(errno.ENOENT, '')

    def truncate(self, path, length, fh=None):
        "Download existing path, truncate and reupload"
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
            self._dirty(path)
            return ESUCCESS
        except:
            raise OSError(errno.ENOENT, '')

    def rmdir(self, path):
        if path in self.__newfolders: # folder was just created, not synced yet
            self.__newfolders.remove(path)
            self._dirty(path)
            return
        try:
            f = self._getpath(path)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        r = f.delete()
        self._dirty(path)
        return ESUCCESS

    def unlink(self, path):
        if path in self.__newfiles.keys(): # file was just created, not synced yet
            del self.__newfiles[path]
            self._dirty(path)
            return
        try:
            f = self._getpath(path)
        except JFS.JFSError:
            raise OSError(errno.ENOENT, '')
        r = f.delete()
        self._dirty(path)
        return ESUCCESS

    def write(self, path, data, offset, fh=None):
        if is_blacklisted(path):
            raise JottaFuseError('Blacklisted file')
        if not self.__newfiles.has_key(path):
            self.__newfiles[path] = StringIO()

        buf = self.__newfiles[path]
        buf.seek(offset)
        buf.write(data)
        self._dirty(path)
        return len(data)

