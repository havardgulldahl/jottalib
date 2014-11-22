#!/usr/bin/env python
# encoding: utf-8
"""A service to sync a local file tree to jottacloud.

Run by crontab at some interval.

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
# Copyright 2014 Håvard Gulldahl <havard@gulldahl.no>

import os, os.path, sys, logging, argparse, netrc

from jottalib.JFS import JFS
from jottacloudclient import jottacloud, __version__

if __name__=='__main__':
    def is_dir(path):
        if not os.path.isdir(path):
            raise argparse.ArgumentTypeError('%s is not a valid directory' % path)
        return path
    parser = argparse.ArgumentParser(description=__doc__,
                                    epilog='The program expects to find an entry for "jottacloud" in your .netrc, or JOTTACLOUD_USERNAME and JOTTACLOUD_PASSWORD in the running environment.')
    parser.add_argument('--loglevel', type=int, help='Loglevel', default=logging.WARNING)
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--dry-run', action='store_true',
                        help="don't actually do any uploads or deletes, just show what would be done")
    parser.add_argument('topdir', type=is_dir, help='Path to local dir that needs syncing')
    parser.add_argument('jottapath', help='The path at JottaCloud where the tree shall be synced (must exist)')
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    try:
        n = netrc.netrc()
        username, account, password = n.authenticators('jottacloud') # read .netrc entry for 'machine jottacloud'
    except:
        raise
        username = os.environ['JOTTACLOUD_USERNAME']
        password = os.environ['JOTTACLOUD_PASSWORD']

    jfs = JFS(username, password)

    for onlylocal, onlyremote, bothplaces in jottacloud.compare(args.topdir, args.jottapath, jfs):
        print onlylocal, onlyremote, bothplaces
        print "uploading %s onlylocal files" % len(onlylocal)
        for f in onlylocal:
            logging.debug("uploading new file: %s", f)
            if not args.dry_run:
                jottacloud.new(f.localpath, f.jottapath, jfs)
        print "deleting %s onlyremote files" % len(onlyremote)
        for f in onlyremote:
            logging.debug("deleting cloud file that has disappeared locally: %s", f)
            if not args.dry_run:
                jottacloud.delete(f.jottapath, jfs)
        print "comparing %s bothplaces files" % len(bothplaces)
        for f in bothplaces:
            logging.debug("checking whether file contents has changed: %s", f)
            if not args.dry_run:
                jottacloud.replace_if_changed(f.localpath, f.jottapath, jfs)

