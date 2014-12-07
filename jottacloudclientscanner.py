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

from clint.textui import progress, puts, colored
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
    parser.add_argument('--no-unicode', action='store_true',
                        help="don't use unicode output")
    parser.add_argument('topdir', type=is_dir, help='Path to local dir that needs syncing')
    parser.add_argument('jottapath', help='The path at JottaCloud where the tree shall be synced (must exist)')
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    try:
        n = netrc.netrc()
        username, account, password = n.authenticators('jottacloud') # read .netrc entry for 'machine jottacloud'
    except Exception as e:
        logging.exception(e)
        username = os.environ['JOTTACLOUD_USERNAME']
        password = os.environ['JOTTACLOUD_PASSWORD']

    jfs = JFS(username, password)

    if not args.no_unicode: # use pretty characters to show progress
        progress.BAR_EMPTY_CHAR=u'○'
        progress.BAR_FILLED_CHAR=u'●'

    errors = {}
    def saferun(cmd, *args):
        logging.debug('running %s with args %s', cmd, args)
        try:
            return apply(cmd, args)
        except Exception as e:
            puts(colored.red('Ouch. Something\'s wrong with "%s":' % args[0]))
            logging.exception(e)
            errors.update( {args[0]:e} )
            return False

    try:
        for dirpath, onlylocal, onlyremote, bothplaces in jottacloud.compare(args.topdir, args.jottapath, jfs):
            puts(colored.green("Entering dir: %s" % dirpath))
            if len(onlylocal):
                for f in progress.bar(onlylocal, label="uploading %s new files: " % len(onlylocal)):
                    logging.debug("uploading new file: %s", f)
                    if not args.dry_run:
                        saferun(jottacloud.new, f.localpath, f.jottapath, jfs)
            if len(onlyremote):
                puts(colored.red("deleting %s removed files: " % len(onlyremote)))
                for f in progress.bar(onlyremote):
                    logging.debug("deleting cloud file that has disappeared locally: %s", f)
                    if not args.dry_run:
                        saferun(jottacloud.delete, f.jottapath, jfs)
            if len(bothplaces):
                for f in progress.bar(bothplaces, label="comparing %s existing files: " % len(bothplaces)):
                    logging.debug("checking whether file contents has changed: %s", f)
                    if not args.dry_run:
                        saferun(jottacloud.replace_if_changed, f.localpath, f.jottapath, jfs)
    except KeyboardInterrupt:
        # Ctrl-c pressed, cleaning up
        pass
    puts('Finished, with %s errors' % len(errors))

