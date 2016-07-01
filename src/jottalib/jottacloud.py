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
# Copyright 2014-2016 Håvard Gulldahl <havard@gulldahl.no>

import sys, os, os.path, posixpath, logging, collections

log = logging.getLogger(__name__)

import chardet # get this module: pip install chardet

try:
    from xattr import xattr # get this module: pip install xattr
    HAS_XATTR=True
except ImportError: # no xattr installed, not critical because it is optional
    HAS_XATTR=False

import jottalib
from jottalib.JFS import JFSNotFoundError, \
                         JFSFolder, JFSFile, JFSIncompleteFile, JFSFileDirList, \
                         calculate_md5


#A namedtuple to keep a link between a local path and its online counterpart
#localpath will be a byte string with utf8 code points
#jottapath will be a unicode string
SyncFile = collections.namedtuple('SyncFile', 'localpath, jottapath')

def sf(f, dirpath, jottapath):
    """Create and return a SyncFile tuple from filename.

            localpath will be a byte string with utf8 code points
            jottapath will be a unicode string"""
    log.debug('Create SyncFile from %s', repr(f))
    log.debug('Got encoded filename %r, joining with dirpath %r', _encode_filename_to_filesystem(f), dirpath)
    return SyncFile(localpath=os.path.join(dirpath, _encode_filename_to_filesystem(f)),
                  jottapath=posixpath.join(_decode_filename_to_unicode(jottapath), _decode_filename_to_unicode(f)))


def get_jottapath(localtopdir, dirpath, jottamountpoint):
    """Translate localtopdir to jottapath. Returns unicode string"""
    log.debug("get_jottapath %r %r %r", localtopdir, dirpath, jottamountpoint)
    normpath =  posixpath.normpath(posixpath.join(jottamountpoint, posixpath.basename(localtopdir),
                                   posixpath.relpath(dirpath, localtopdir)))
    return _decode_filename_to_unicode(normpath)


def is_file(jottapath, JFS):
    """Check if a file exists on jottacloud"""
    log.debug("is_file %r", jottapath)
    try:
        jf = JFS.getObject(jottapath)
    except JFSNotFoundError:
        return False
    return isinstance(jf, JFSFile)

def filelist(jottapath, JFS):
    """Get a set() of files from a jottapath (a folder)"""
    log.debug("filelist %r", jottapath)
    try:
        jf = JFS.getObject(jottapath)
    except JFSNotFoundError:
        return set() # folder does not exist, so pretend it is an empty folder
    if not isinstance(jf, JFSFolder):
        return False
    return set([f.name for f in jf.files() if not f.is_deleted()]) # Only return files that aren't deleted

def folderlist(jottapath, JFS):
    """Get a set() of folders from a jottapath (a folder)"""
    logging.debug("folderlist %r", jottapath)
    try:
        jf = JFS.getObject(jottapath)
    except JFSNotFoundError:
        return set() # folder does not exist, so pretend it is an empty folder
    if not isinstance(jf, JFSFolder):
        return False
    return set([f.name for f in jf.folders() if not f.is_deleted()]) # Only return files that aren't deleted

def compare(localtopdir, jottamountpoint, JFS, followlinks=False, exclude_patterns=None):
    """Make a tree of local files and folders and compare it with what's currently on JottaCloud.

    For each folder, yields:
        dirpath, # byte string, full path
        onlylocal, # set(), files that only exist locally, i.e. newly added files that don't exist online,
        onlyremote, # set(), files that only exist in the JottaCloud, i.e. deleted locally
        bothplaces # set(), files that exist both locally and remotely
        onlyremotefolders, # set(), folders that only exist in the JottaCloud, i.e. deleted locally
    """
    def excluded(unicodepath, fname):
        fpath = os.path.join(unicodepath, _decode_filename_to_unicode(fname))
        if exclude_patterns is None:
            return False
        for p in exclude_patterns:
            if p.search(fpath):
                log.debug("%r excluded by pattern %r", fpath, p.pattern)
                return True
        return False
    bytestring_localtopdir = _encode_filename_to_filesystem(localtopdir)
    for dirpath, dirnames, filenames in os.walk(bytestring_localtopdir, followlinks=followlinks):
        # to keep things explicit, and avoid encoding/decoding issues,
        # keep a bytestring AND a unicode variant of dirpath
        dirpath = _encode_filename_to_filesystem(dirpath)
        unicodepath = _decode_filename_to_unicode(dirpath)
        log.debug("compare walk: %r -> %s files ", unicodepath, len(filenames))

        # create set()s of local files and folders
        # paths will be unicode strings
        localfiles = set([f for f in filenames if not excluded(unicodepath, f)]) # these are on local disk
        localfolders = set([f for f in dirnames if not excluded(unicodepath, f)]) # these are on local disk
        jottapath = get_jottapath(localtopdir, unicodepath, jottamountpoint) # translate to jottapath
        log.debug("compare jottapath: %r", jottapath)

        # create set()s of remote files and folders
        # paths will be unicode strings
        cloudfiles = filelist(jottapath, JFS) # set(). these are on jottacloud
        cloudfolders = folderlist(jottapath, JFS)

        log.debug("--cloudfiles: %r", cloudfiles)
        log.debug("--localfiles: %r", localfiles)
        log.debug("--cloudfolders: %r", cloudfolders)

        onlylocal = [ sf(f, dirpath, jottapath) for f in localfiles.difference(cloudfiles)]
        onlyremote = [ sf(f, dirpath, jottapath) for f in cloudfiles.difference(localfiles)]
        bothplaces = [ sf(f, dirpath, jottapath) for f in localfiles.intersection(cloudfiles)]
        onlyremotefolders = [ sf(f, dirpath, jottapath) for f in cloudfolders.difference(localfolders)]
        yield dirpath, onlylocal, onlyremote, bothplaces, onlyremotefolders


def _decode_filename_to_unicode(f):
    '''Get bytestring filename and return unicode.
    First, try to decode from default file system encoding
    If that fails, use ``chardet`` module to guess encoding.
    As a last resort, try to decode as utf-8.

    If the argument already is unicode, return as is'''

    log.debug('_decode_filename_to_unicode(%s)', repr(f))
    if isinstance(f, unicode):
        return f
    try:
        return f.decode(sys.getfilesystemencoding())
    except UnicodeDecodeError:
        charguess = chardet.detect(f)
        log.debug("chardet filename: %r -> %r", f, charguess)
        if charguess['encoding'] is not None:
            try:
                return f.decode(charguess['encoding'])
            except UnicodeDecodeError:
                pass
        log.warning('Cannot understand decoding of this filename: %r (guessed %r, but was wrong)',
                    f, charguess)
        log.debug('Trying utf-8 to decode %r', f)
        try:
            return f.decode('utf-8')
        except UnicodeDecodeError:
            pass
        log.debug('Trying latin1 to decode %r', f)
        try:
            return f.decode('latin1')
        except UnicodeDecodeError:
            log.warning('Exhausted all options. Decoding %r to safe ascii', f)
            return f.decode('ascii', errors='ignore')


def _encode_filename_to_filesystem(f):
    '''Get a unicode filename and return bytestring, encoded to file system default.

    If the argument already is a bytestring, return as is'''
    log.debug('_encode_filename_to_filesystem(%s)', repr(f))
    if isinstance(f, str):
        return f
    try:
        return f.encode(sys.getfilesystemencoding())
    except UnicodeEncodeError:
        raise

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
