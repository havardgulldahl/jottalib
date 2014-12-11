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

import sys, os, os.path, hashlib, logging, collections

import jottalib
from jottalib.JFS import JFSNotFoundError, JFSFolder, JFSFile, JFSIncompleteFile


SyncFile = collections.namedtuple('SyncFile', 'localpath, jottapath')


def get_jottapath(localtopdir, dirpath, jottamountpoint):
    """Translate localtopdir to jottapath"""
    logging.debug("get_jottapath %s %s %s", localtopdir, dirpath, jottamountpoint)
    return os.path.normpath(os.path.join(jottamountpoint, os.path.basename(localtopdir),
                                         os.path.relpath(dirpath, localtopdir)))

def is_file(jottapath, JFS):
    """Check if a file exists on jottacloud"""
    logging.debug("is_file %s", jottapath)
    try:
        jf = JFS.getObject(jottapath)
    except JFSNotFoundError:
        return False
    return isinstance(jf, JFSFile)

def filelist(jottapath, JFS):
    """Get a set() of files from a jottapath (a folder)"""
    #logging.debug("filelist %s", jottapath)
    try:
        jf = JFS.getObject(jottapath)
    except JFSNotFoundError:
        return set() # folder does not exist, so pretend it is an empty folder
    if not isinstance(jf, JFSFolder):
        return False
    return set([f.name for f in jf.files() if not f.is_deleted()]) # Only return files that aren't deleted

def compare(localtopdir, jottamountpoint, JFS, followlinks=False):
    """Make a tree of local files and folders and compare it with what's currently on JottaCloud.

    For each folder, yields three set()s:
        onlylocal, # files that only exist locally, i.e. newly added files that don't exist online,
        onlyremote, # files that only exist in the JottaCloud, i.e. deleted locally
        bothplaces # files that exist both locally and remotely
    """
    for dirpath, dirnames, filenames in os.walk(localtopdir, followlinks=followlinks):
        dirpath = dirpath.decode(sys.getfilesystemencoding())
        logging.debug("compare walk: %s -> %s files ", dirpath, len(filenames))
        localfiles = set([f.decode(sys.getfilesystemencoding()) for f in filenames]) # these are on local disk
        jottapath = get_jottapath(localtopdir, dirpath, jottamountpoint) # translate to jottapath
        logging.debug("compare jottapath: %s", jottapath)
        cloudfiles = filelist(jottapath, JFS) # set(). these are on jottacloud

        def sf(f):
            """Create SyncFile tuple from filename"""
            return SyncFile(localpath=os.path.join(dirpath, f),
                            jottapath=os.path.join(jottapath, f))
        logging.debug("--cloudfiles: %s", cloudfiles)
        logging.debug("--localfiles: %s", localfiles)
        onlylocal = [ sf(f) for f in localfiles.difference(cloudfiles)]
        onlyremote = [ sf(f) for f in cloudfiles.difference(localfiles)]
        bothplaces = [ sf(f) for f in localfiles.intersection(cloudfiles)]
        yield dirpath, onlylocal, onlyremote, bothplaces

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
    with open(localfile) as lf:
        lf_hash = hashlib.md5(lf.read()).hexdigest()
    if type(jf) == JFSIncompleteFile:
        logging.debug("Local file %s is incompletely uploaded, continue", localfile)
        return resume(localfile, jf, JFS)
    elif jf.md5 == lf_hash: # hashes are the same
        logging.debug("hash match (%s), file contents haven't changed", lf_hash)
        return jf         # return the version from jottaclouds
    else:
        return new(localfile, jottapath, JFS)

def delete(jottapath, JFS):
    """Remove file from JottaCloud because it is no longer present on local disk.
    Returns boolean"""
    jf = JFS.post('%s?dl=true' % jottapath)
    return jf.is_deleted()
