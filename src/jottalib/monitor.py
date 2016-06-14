#!/usr/bin/env python
# encoding: utf-8
"""A service to act on changes on local tree (using inotify or OS equivalent) and update JottaCloud tree accordingly.

"""
#
# This file is part of jottalib.
#
# jottalib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# jottalib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with jottalib.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2015 Håvard Gulldahl <havard@gulldahl.no>

import time, os, os.path, sys, logging, argparse, posixpath

log = logging.getLogger(__name__)

from watchdog.observers import Observer # pip install watchdog
from watchdog.utils import platform
from watchdog.events import LoggingEventHandler, FileSystemEventHandler

from clint.textui import progress, puts, colored

from jottalib.JFS import JFS
from jottalib import jottacloud, __version__
from jottalib.contrib.readlnk import readlnk




"""


1. monitor a directory
2. if a new file enters, upload it to the cloud
2b. if --archive, delete it from the directory
3. if a file is renamed, rename it in the cloud
4. if a file is changed, upload the new file
5. if a file is deleted...

ARCHIVE

SHARE

SYNC
keep a tree in sync


"""

class ArchiveEventHandler(FileSystemEventHandler):
    '''Handles Archive events. Heuristics for this handler:

    new file: upload to cloud and delete locally

    Pro tip: If your create a symlink or a .lnk reference to the file you want to upload,
             the upload will start straight away. Works great for big files.

    '''
    mode = 'Archive'

    def __init__(self, jfs, topdir, jottaroot=None):
        super(ArchiveEventHandler, self).__init__()
        self.jfs = jfs
        self.topdir = topdir
        self.jottaroot = jottaroot and jottaroot or ('/Jotta/%s' % self.mode)

    def get_jottapath(self, p, filename=None):
        rel = os.path.relpath(p, self.topdir) # strip leading path
        parts = [self.jottaroot, ] + list(os.path.split(rel)) # explode path to normalize OS path separators
        if filename is not None:
            parts.pop()  # remove original filename
            parts.append(filename)  # and replace with provided one
        return posixpath.join(*parts)  # return url

    def on_modified(self, event, dry_run=False, remove_uploaded=True):
        'Called when a file (or directory) is modified. '
        super(ArchiveEventHandler, self).on_modified(event)
        src_path = event.src_path
        if event.is_directory:
            if not platform.is_darwin():
                log.info("event is a directory, safe to ignore")
                return
            # OSX is behaving erratically and we need to paper over it.
            # the OS only reports every other file event,
            # but always fires off a directory event when a file has changed. (OSX 10.9 tested)
            # so we need to find the actual file changed and then go on from there
            files = [event.src_path+"/"+f for f in os.listdir(event.src_path)]
            try:
                src_path = max(files, key=os.path.getmtime)
            except (OSError, ValueError) as e: # broken symlink or directory empty
                return
        log.info('Modified file detectd: %s', src_path)
        #
        # we're receiving events at least two times: on file open and on file close.
        # OSes might report even more
        # we're only interested in files that are closed (finished), so we try to
        # open it. if it is locked, we can infer that someone is still writing to it.
        # this works on platforms: windows, ... ?
        # TODO: investigate http://stackoverflow.com/a/3876461 for POSIX support
        try:
            open(src_path)   # win exclusively
            os.open(src_path, os.O_EXLOCK) # osx exclusively
        except IOError: # file is not finished
            log.info('File is not finished')
            return
        except AttributeError: # no suuport for O_EXLOCK (only BSD)
            pass
        return self._new(src_path, dry_run, remove_uploaded)

    def on_created(self, event, dry_run=False, remove_uploaded=True):
        'Called when a file (or directory) is created. '
        super(ArchiveEventHandler, self).on_created(event)
        log.info("created: %s", event)

    def _new(self, src_path, dry_run=False, remove_uploaded=False):
            'Code to upload'
            # are we getting a symbolic link?
            if os.path.islink(src_path):
                sourcefile = os.path.normpath(os.path.join(self.topdir, os.readlink(src_path)))
                if not os.path.exists(sourcefile): # broken symlink
                    log.error("broken symlink %s->%s", src_path, sourcefile)
                    raise IOError("broken symliknk %s->%s", src_path, sourcefile)
                jottapath = self.get_jottapath(src_path, filename=os.path.basename(sourcefile))
            elif os.path.splitext(src_path)[1].lower() == '.lnk':
                # windows .lnk
                sourcefile = os.path.normpath(readlnk(src_path))
                if not os.path.exists(sourcefile): # broken symlink
                    log.error("broken fat32lnk %s->%s", src_path, sourcefile)
                    raise IOError("broken fat32lnk %s->%s", src_path, sourcefile)
                jottapath = self.get_jottapath(src_path, filename=os.path.basename(sourcefile))
            else:
                sourcefile = src_path
                if not os.path.exists(sourcefile): # file not exis
                    log.error("file does not exist: %s", sourcefile)
                    raise IOError("file does not exist: %s", sourcefile)
                jottapath = self.get_jottapath(src_path)

            log.info('Uploading file %s to %s', sourcefile, jottapath)
            if not dry_run:
                if not jottacloud.new(sourcefile, jottapath, self.jfs):
                    log.error('Uploading file %s failed', sourcefile)
                    raise
            if remove_uploaded:
                log.info('Removing file after upload: %s', src_path)
                if not dry_run:
                    os.remove(src_path)

class ShareEventHandler(FileSystemEventHandler):
    '''Handles Share events. Heuristics for this handler:

    new file: upload to cloud and replace contents with public share url
    delete file: delete from cloud
    '''
    def __init__(self, jfs, topdir, jottaroot=None):
        raise NotImplementedError

class SyncEventHandler(FileSystemEventHandler):
    '''Handles Sync events. Heuristics for this handler:

    new file: upload it to the cloud
    file is renamed: rename it in the cloud
    file is changed: upload the new file
    file is deleted: delete it from the cloud
    '''
    def __init__(self, jfs, topdir, jottaroot=None):
        raise NotImplementedError

def humanizeFileSize(size):
    size = abs(size)
    if (size==0):
        return "0B"
    units = ['B','KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB']
    p = math.floor(math.log(size, 2)/10)
    return "%.3f%s" % (size/math.pow(1024,p),units[int(p)])


def filemonitor(topdir, mode, jfs):
    errors = {}
    def saferun(cmd, *args):
        log.debug('running %s with args %s', cmd, args)
        try:
            return apply(cmd, args)
        except Exception as e:
            puts(colored.red('Ouch. Something\'s wrong with "%s":' % args[0]))
            log.exception('SAFERUN: Got exception when processing %s', args)
            errors.update( {args[0]:e} )
            return False

    if mode == 'archive':
        event_handler = ArchiveEventHandler(jfs, topdir)
    elif mode == 'sync':
        event_handler = SyncEventHandler(jfs, topdir)
        #event_handler = LoggingEventHandler()
    elif mode == 'share':
        event_handler = ShareEventHandler(jfs, topdir)
    observer = Observer()
    observer.schedule(event_handler, topdir, recursive=True)
    observer.start()
    try:
        puts(colored.green('Starting JottaCloud monitor'))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        puts(colored.red('JottaCloud monitor stopped'))
    observer.join()
