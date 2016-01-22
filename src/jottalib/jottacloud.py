# encoding: utf-8
"""Stuff to communicate with JottaCloud servers"""
#
# This file is part of jottabox.
#
# jottabox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# jottabox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with jottabox.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014 Håvard Gulldahl <havard@gulldahl.no>

import sys, os, os.path, posixpath, logging, collections

log = logging.getLogger(__name__)

try:
    from xattr import xattr # pip install xattr
    HAS_XATTR=True
except ImportError: # no xattr installed, not critical because it is optional
    HAS_XATTR=False


import jottalib
from jottalib.JFS import JFSNotFoundError, \
                         JFSFolder, JFSFile, JFSIncompleteFile, JFSFileDirList, \
                         calculate_md5


SyncFile = collections.namedtuple('SyncFile', 'localpath, jottapath')


def get_jottapath(localtopdir, dirpath, jottamountpoint):
    """Translate localtopdir to jottapath"""
    log.debug("get_jottapath %s %s %s", localtopdir, dirpath, jottamountpoint)
    return posixpath.normpath(posixpath.join(jottamountpoint, posixpath.basename(localtopdir),
                                         posixpath.relpath(dirpath, localtopdir)))

def is_file(jottapath, JFS):
    """Check if a file exists on jottacloud"""
    log.debug("is_file %s", jottapath)
    try:
        jf = JFS.getObject(jottapath)
    except JFSNotFoundError:
        return False
    return isinstance(jf, JFSFile)

def filelist(jottapath, JFS):
    """Get a set() of files from a jottapath (a folder)"""
    log.debug("filelist %s", jottapath)
    try:
        jf = JFS.getObject(jottapath)
    except JFSNotFoundError:
        return set() # folder does not exist, so pretend it is an empty folder
    if not isinstance(jf, JFSFolder):
        return False
    return set([f.name for f in jf.files() if not f.is_deleted()]) # Only return files that aren't deleted

def folderlist(jottapath, JFS):
    """Get a set() of folders from a jottapath (a folder)"""
    logging.debug("folderlist %s", jottapath)
    try:
        jf = JFS.getObject(jottapath)
    except JFSNotFoundError:
        return set() # folder does not exist, so pretend it is an empty folder
    if not isinstance(jf, JFSFolder):
        return False
    return set([f.name for f in jf.folders() if not f.is_deleted()]) # Only return files that aren't deleted

def compare(localtopdir, jottamountpoint, JFS, followlinks=False, exclude_patterns=None):
    """Make a tree of local files and folders and compare it with what's currently on JottaCloud.

    For each folder, yields three set()s:
        onlylocal, # files that only exist locally, i.e. newly added files that don't exist online,
        onlyremote, # files that only exist in the JottaCloud, i.e. deleted locally
        bothplaces # files that exist both locally and remotely
    """
    def excluded(dirpath, fname):
        fpath = os.path.join(dirpath, _decode_filename(fname))
        if exclude_patterns is None:
            return False
        for p in exclude_patterns:
            if p.search(fpath):
                log.debug("%r excluded by pattern %r", fpath, p.pattern)
                return True
        return False
    for dirpath, dirnames, filenames in os.walk(localtopdir, followlinks=followlinks):
        dirpath = dirpath.decode(sys.getfilesystemencoding())
        log.debug("compare walk: %s -> %s files ", dirpath, len(filenames))
        localfiles = set([_decode_filename(f) for f in filenames if not excluded(dirpath, f)]) # these are on local disk
        localfolders = set([_decode_filename(f) for f in dirnames if not excluded(dirpath, f)]) # these are on local disk
        jottapath = get_jottapath(localtopdir, dirpath, jottamountpoint) # translate to jottapath
        log.debug("compare jottapath: %s", jottapath)
        cloudfiles = filelist(jottapath, JFS) # set(). these are on jottacloud
        cloudfolders = folderlist(jottapath, JFS)

        def sf(f):
            """Create SyncFile tuple from filename"""
            return SyncFile(localpath=os.path.join(dirpath, f),
                            jottapath=posixpath.join(jottapath, f))
        log.debug("--cloudfiles: %s", cloudfiles)
        log.debug("--localfiles: %s", localfiles)
        logging.debug("--cloudfolders: %s", cloudfolders)

        onlylocal = [ sf(f) for f in localfiles.difference(cloudfiles)]
        onlyremote = [ sf(f) for f in cloudfiles.difference(localfiles)]
        bothplaces = [ sf(f) for f in localfiles.intersection(cloudfiles)]
        onlyremotefolders = [ sf(f) for f in cloudfolders.difference(localfolders)]
        yield dirpath, onlylocal, onlyremote, bothplaces, onlyremotefolders


def _decode_filename(f):
    return f.decode(sys.getfilesystemencoding())


def new(localfile, jottapath, JFS):
    """Upload a new file from local disk (doesn't exist on JottaCloud).

    Returns JottaFile object"""
    with open(localfile) as lf:
        _new = JFS.up(jottapath, lf)
    return _new

def resume(localfile, jottafile, JFS):
    """Continue uploading a new file from local file (already exists on JottaCloud"""
    with open(localfile) as lf:
        _complete = jottafile.resume(lf)
    return _complete

def replace_if_changed(localfile, jottapath, JFS):
    """Compare md5 hash to determine if contents have changed.
    Upload a file from local disk and replace file on JottaCloud if the md5s differ,
    or continue uploading if the file is incompletely uploaded.

    Returns the JottaFile object"""
    jf = JFS.getObject(jottapath)
    lf_hash = getxattrhash(localfile) # try to read previous hash, stored in xattr
    if lf_hash is None:               # no valid hash found in xattr,
        with open(localfile) as lf:
            lf_hash = calculate_md5(lf) # (re)calculate it
    if type(jf) == JFSIncompleteFile:
        log.debug("Local file %s is incompletely uploaded, continue", localfile)
        return resume(localfile, jf, JFS)
    elif jf.md5 == lf_hash: # hashes are the same
        log.debug("hash match (%s), file contents haven't changed", lf_hash)
        setxattrhash(localfile, lf_hash)
        return jf         # return the version from jottaclouds
    else:
        setxattrhash(localfile, lf_hash)
        return new(localfile, jottapath, JFS)

def deleteDir(jottapath, JFS):
    """Remove folder from JottaCloud because it is no longer present on local disk.
    Returns boolean"""
    jf = JFS.post('%s?dlDir=true' % jottapath)
    return jf.is_deleted()

def delete(jottapath, JFS):
    """Remove file from JottaCloud because it is no longer present on local disk.
    Returns boolean"""
    jf = JFS.post('%s?dl=true' % jottapath)
    return jf.is_deleted()

def mkdir(jottapath, JFS):
    """Make a new directory (a.k.a. folder) on JottaCloud.
    Returns boolean"""
    jf = JFS.post('%s?mkDir=true' % jottapath)
    return instanceof(jf, JFSFolder)

def iter_tree(jottapath, JFS):
    """Get a tree of of files and folders. use as an iterator, you get something like os.walk"""
    filedirlist = JFS.getObject('%s?mode=list' % jottapath)
    log.debug("got tree: %s", filedirlist)
    if not isinstance(filedirlist, JFSFileDirList):
        yield ( '', tuple(), tuple() )
    for path in filedirlist.tree:
        yield path

def setxattrhash(filename, md5hash):
    log.debug('set xattr hash for %s', filename)
    if not HAS_XATTR:
        log.info("xattr not found. Installing it will speed up hash comparison: pip install xattr")
        return False
    try:
        x = xattr(filename)
        x.set('user.jottalib.md5', md5hash)
        x.set('user.jottalib.timestamp', str(os.path.getmtime(filename)))
        x.set('user.jottalib.filesize', str(os.path.getsize(filename)))
        return True
    except IOError:
        # no file system support
        return False
    except Exception as e:
        log.exception(e)
        #log.debug('setxattr got exception %r', e)
    return False

def getxattrhash(filename):
    log.debug('get xattr hash for %s', filename)
    if not HAS_XATTR:
        log.info("xattr not found. Installing it will speed up hash comparison: pip install xattr")
        return None
    try:
        x = xattr(filename)
        if x.get('user.jottalib.filesize') != str(os.path.getsize(filename)) or x.get('user.jottalib.timestamp') != str(os.path.getmtime(filename)):
            x.remove('user.jottalib.filesize')
            x.remove('user.jottalib.timestamp')
            x.remove('user.jottalib.md5')
            return None # this is not the file we have calculated md5 for
        return x.get('user.jottalib.md5')
    except Exception as e:
        log.debug('setxattr got exception %r', e)
        return None
