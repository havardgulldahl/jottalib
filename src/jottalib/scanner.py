#!/usr/bin/env python
# encoding: utf-8
"""A service to sync a local file tree to jottacloud.

Copies and updates files in the cloud by comparing md5 hashes, like the official client.
Run it from crontab at an appropriate interval.

"""
# This file is part of jottacloudclient.
#
# jottacloudclient is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# jottacloudclient is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with jottacloudclient.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2015 Håvard Gulldahl <havard@gulldahl.no>

#import included batteries
import os, re, os.path, sys, logging, argparse
import math, time

log = logging.getLogger(__name__)

#import pip modules
from clint.textui import progress, puts, colored

#import jottalib
from jottalib.JFS import JFS
from . import jottacloud, __version__


if sys.platform != "win32":
    # change progress indicators to something that looks nice
    #TODO: rather detect utf-8 support in the terminal
    #TODO: change this when https://github.com/kennethreitz/clint/pull/151 is merged
    progress.BAR_EMPTY_CHAR =u'○'
    progress.BAR_FILLED_CHAR=u'●'


def humanizeFileSize(size):
    size = abs(size)
    if (size==0):
        return "0B"
    units = ['B','KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB']
    p = math.floor(math.log(size, 2)/10)
    return "%.3f%s" % (size/math.pow(1024,p),units[int(p)])

def filescanner(topdir, jottapath, jfs, errorfile, exclude=None, dry_run=False, prune_files=True, prune_folders=True ):

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

    _files = 0

    try:
        for dirpath, onlylocal, onlyremote, bothplaces, onlyremotefolders in jottacloud.compare(topdir, jottapath, jfs, exclude_patterns=exclude):
            puts(colored.green("Entering dir: %s" % dirpath))
            if len(onlylocal):
                _start = time.time()
                _uploadedbytes = 0
                for f in progress.bar(onlylocal, label="uploading %s new files: " % len(onlylocal)):
                    if os.path.islink(f.localpath):
                        log.debug("skipping symlink: %s", f)
                        continue
                    log.debug("uploading new file: %s", f)
                    if not dry_run:
                        if saferun(jottacloud.new, f.localpath, f.jottapath, jfs) is not False:
                            _uploadedbytes += os.path.getsize(f.localpath)
                            _files += 1
                _end = time.time()
                puts(colored.magenta("Network upload speed %s/sec" % ( humanizeFileSize( (_uploadedbytes / (_end-_start)) ) )))

            if prune_files and len(onlyremote):
                puts(colored.red("Deleting %s files from JottaCloud because they no longer exist locally " % len(onlyremote)))
                for f in progress.bar(onlyremote, label="deleting JottaCloud file: "):
                    log.debug("deleting cloud file that has disappeared locally: %s", f)
                    if not dry_run:
                        if saferun(jottacloud.delete, f.jottapath, jfs) is not False:
                            _files += 1
            if len(bothplaces):
                for f in progress.bar(bothplaces, label="comparing %s existing files: " % len(bothplaces)):
                    log.debug("checking whether file contents has changed: %s", f)
                    if not dry_run:
                        if saferun(jottacloud.replace_if_changed, f.localpath, f.jottapath, jfs) is not False:
                            _files += 1
            if prune_folders and len(onlyremotefolders):
                puts(colored.red("Deleting %s folders from JottaCloud because they no longer exist locally " % len(onlyremotefolders)))
                for f in onlyremotefolders:
                    if not dry_run:
                        if saferun(jottacloud.deleteDir, f.jottapath, jfs) is not False:
                            logging.debug("Deleted remote folder %s", f.jottapath)
    except KeyboardInterrupt:
        # Ctrl-c pressed, cleaning up
        pass
    if len(errors) == 0:
        puts('Finished syncing %s files to JottaCloud, no errors. yay!' % _files)
    else:
        puts(('Finished syncing %s files, ' % _files )+
             colored.red('with %s errors (read %s for details)' % (len(errors), errorfile, )))
