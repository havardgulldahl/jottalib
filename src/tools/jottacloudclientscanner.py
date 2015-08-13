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

import os, os.path, sys, logging, argparse, netrc
import math, time, signal, datetime
from concurrent import futures

logging.captureWarnings(True)
from clint.textui import progress, puts, colored
from jottalib.JFS import JFS
from jottacloudclient import jottacloud, __version__


def humanizeFileSize(size):
    size = abs(size)
    if (size==0):
        return "0B"
    units = ['B','KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB']
    p = math.floor(math.log(size, 2)/10)
    return "%.3f%s" % (size/math.pow(1024,p),units[int(p)])

if __name__=='__main__':
    def is_dir(path):
        if not os.path.isdir(path):
            raise argparse.ArgumentTypeError('%s is not a valid directory' % path)
        return path
    parser = argparse.ArgumentParser(description=__doc__,
                                    epilog="""The program expects to find an entry for "jottacloud" in your .netrc,
                                    or JOTTACLOUD_USERNAME and JOTTACLOUD_PASSWORD in the running environment.
                                    This is not an official JottaCloud project.""")
    parser.add_argument('--loglevel', type=int, help='Loglevel from 1 (only errors) to 9 (extremely chatty)', default=logging.WARNING)
    parser.add_argument('--errorfile', help='A file to write errors to', default='./jottacloudclient.log')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--dry-run', action='store_true',
                        help="don't actually do any uploads or deletes, just show what would be done")
    parser.add_argument('--no-unicode', action='store_true',
                        help="don't use unicode output")
    parser.add_argument('topdir', type=is_dir, help='Path to local dir that needs syncing')
    parser.add_argument('jottapath', help='The path at JottaCloud where the tree shall be synced (must exist)')
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)
    fh = logging.FileHandler(args.errorfile)
    fh.setLevel(logging.ERROR)
    logging.getLogger('').addHandler(fh)

    try:
        n = netrc.netrc()
        username, account, password = n.authenticators('jottacloud') # read .netrc entry for 'machine jottacloud'
    except Exception as e:
        logging.exception(e)
        username = os.environ['JOTTACLOUD_USERNAME']
        password = os.environ['JOTTACLOUD_PASSWORD']

    jfs = JFS(username, password, async_upload=True)

    if not args.no_unicode: # use pretty characters to show progress
        progress.BAR_EMPTY_CHAR=u'○'
        progress.BAR_FILLED_CHAR=u'●'

    errors = {}
    def sigint_handler(signum, frame):
        logging.warning("Quitting after C-C keycombo")
        jfs.session_async.executor.shutdown(wait=False)
        sys.exit(1)
    signal.signal(signal.SIGINT, sigint_handler)
    _files = 0
    dangling_files = []
    from requests.packages import urllib3
    urllib3.disable_warnings() # TODO: remove this before release?
    q = {} # our task queue with Future network operations from requests-futures
    def print_finished(j):
        print "fhinished: %s" % repr(j)

    puts(colored.green("Collecting changes recursively from %s" % args.topdir))

    _start = time.time()
    for dirpath, onlylocal, onlyremote, bothplaces in jottacloud.compare(args.topdir, args.jottapath, jfs):
        puts(colored.green("Entering dir: %s" % dirpath))
        for f in progress.bar(onlylocal,
                              label="Adding new files to upload queue: ",
                              hide=True if len(onlylocal) == 0 else None):
            if os.path.islink(f.localpath):
                logging.debug("skipping symlink: %s", f)
                continue
            if not args.dry_run:
                job = jottacloud.new(f.localpath, f.jottapath, jfs)
                #job.add_done_callback(print_finished)
                q[job] = os.path.getsize(f.localpath) # add jobb to queue, store file size

        dangling_files += list(onlyremote)

        for f in progress.bar(bothplaces,
                              label="Comparing %s existing files: " % len(bothplaces),
                              hide=True if len(bothplaces) == 0 else None):
            if not args.dry_run:
                job = jottacloud.replace_if_changed(f.localpath, f.jottapath, jfs)
                #job.add_done_callback(print_finished)
                if job is not None: #if it is None, file hasnt changd'
                    q[job] = os.path.getsize(f.localpath) ## add jobb to queue, store file size

    _uploadedbytes = 0
    puts(colored.green("Total size to upload: %s" % humanizeFileSize(sum(q.values()))))
    for job in progress.bar(futures.as_completed(q),
                            label="uploading %s new files: " % len(q),
                            hide=True if len(q) == 0 else None,
                            expected_size=len(q)):
        _uploadedbytes = _uploadedbytes + q[job]
        _now = time.time()
        puts(colored.magenta("Current upload speed: %s/s" % ( humanizeFileSize(_uploadedbytes / (_now-_start) ) )))

    for f in progress.bar(dangling_files, label="Deleting dangling JottaCloud files: ",
                         hide=True if len(dangling_files) == 0 else None):
        if not args.dry_run:
            jottacloud.delete(f.jottapath, jfs)

    puts(colored.blue("[%s] Finished syncing files" % datetime.datetime.now().isoformat()))
