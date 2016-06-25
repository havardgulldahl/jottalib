# -*- encoding: utf-8 -*-
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
# Copyright 2011,2013-2016 Håvard Gulldahl <havard@gulldahl.no>

from __future__ import absolute_import, division, unicode_literals

__author__ = 'havard@gulldahl.no'

import argparse
import six
from six.moves import http_client
import humanize as _humanize
import logging
import os
import posixpath
import sys
import time
import re
from clint.textui import progress
from functools import partial

# import our stuff
from jottalib import JFS, __version__
from .scanner import filescanner

HAS_FUSE = False
try:
    from fuse import FUSE # pylint: disable=unused-import
    HAS_FUSE = True
except ImportError:
    pass

HAS_WATCHDOG = False # for monitor()
try:
    import watchdog
    HAS_WATCHDOG = True
except ImportError:
    pass

if sys.platform != "win32":
    # change progress indicators to something that looks nice
    #TODO: rather detect utf-8 support in the terminal
    ProgressBar = partial(progress.Bar, empty_char=u'○', filled_char=u'●')
else:
    ProgressBar = partial(progress.Bar)


## HELPER FUNCTIONS ##

def get_jotta_device(jfs):
    jottadev = None
    for j in jfs.devices: # find Jotta/Shared folder
        if j.name == 'Jotta':
            jottadev = j
    return jottadev


def get_root_dir(jfs):
    jottadev = get_jotta_device(jfs)
    root_dir = jottadev.mountPoints['Sync']
    return root_dir

def parse_args_and_apply_logging_level(parser, argv):
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.loglevel.upper()))
    logging.captureWarnings(True)
    http_client.HTTPConnection.debuglevel = 1 if args.loglevel == 'debug' else 0
    return args


def print_size(num, humanize=False):
    if humanize:
        return _humanize.naturalsize(num, gnu=True)
    else:
        return str(num)

def commandline_text(bytestring):
    'Convert bytestring from command line to unicode, using default file system encoding'
    unicode_string = bytestring.decode(sys.getfilesystemencoding())
    return unicode_string

def is_dir(path):
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError('%s is not a valid directory' % path)
    return path.decode(sys.getfilesystemencoding())

## UTILITIES, ONE PER FUNCTION ##


def fuse(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if not HAS_FUSE:
        message = ['jotta-fuse requires fusepy (pip install fusepy), install that and try again.']
        if os.name == 'nt':
            message.append('Note: jotta-fuse is not supported on Windows, but Cygwin might work.')
        print(' '.join(message))
        sys.exit(1)


    from .jottafuse import JottaFuse
    parser = argparse.ArgumentParser(description=__doc__,
                                     epilog="""The program expects to find an entry for "jottacloud.com" in your .netrc,
                                     or JOTTACLOUD_USERNAME and JOTTACLOUD_PASSWORD in the running environment.
                                     This is not an official JottaCloud project.""")
    parser.add_argument('--debug',
                        action='store_true',
                        help='Run fuse in the foreground and add a lot of messages to help debug')
    parser.add_argument('--debug-fuse',
                        action='store_true',
                        help='Show all low-level filesystem operations')
    parser.add_argument('--debug-http',
                        action='store_true',
                        help='Show all HTTP traffic')
    parser.add_argument('--version',
                        action='version', version=__version__)
    parser.add_argument('mountpoint',
                        type=is_dir,
                        help='A path to an existing directory where you want your JottaCloud tree mounted')
    args = parser.parse_args(argv)
    if args.debug_http:
        http_client.HTTPConnection.debuglevel = 1
    if args.debug:
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
        logging.basicConfig(level=logging.DEBUG)

    auth = JFS.get_auth_info()
    fuse = FUSE(JottaFuse(auth), args.mountpoint, debug=args.debug_fuse,
                sync_read=True, foreground=args.debug, raw_fi=False,
                fsname="JottaCloudFS", subtype="fuse")

def upload(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Upload a file to JottaCloud.')
    parser.add_argument('localfile',
                        help='The local file that you want to upload',
                        type=argparse.FileType('r'))
    parser.add_argument('remote_dir',
                        help='The remote directory to upload the file to',
                        nargs='?',
                        type=commandline_text)
    parser.add_argument('-l', '--loglevel',
                        help='Logging level. Default: %(default)s.',
                        choices=('debug', 'info', 'warning', 'error'),
                        default='warning')
    jfs = JFS.JFS()
    args = parse_args_and_apply_logging_level(parser, argv)
    decoded_filename = commandline_text(args.localfile.name)
    progress_bar = ProgressBar()
    callback = lambda monitor, size: progress_bar.show(monitor.bytes_read, size)
    root_folder = get_root_dir(jfs)
    if args.remote_dir:
        target_dir_path = posixpath.join(root_folder.path, args.remote_dir)
        target_dir = jfs.getObject(target_dir_path)
    else:
        target_dir = root_folder
    upload = target_dir.up(args.localfile, os.path.basename(decoded_filename), upload_callback=callback)
    print('%s uploaded successfully' % decoded_filename)
    return True # TODO: check return value


def share(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Share a file on JottaCloud and get the public URI.',
                                     epilog='Note: This utility needs to find JOTTACLOUD_USERNAME'
                                     ' and JOTTACLOUD_PASSWORD in the running environment.')
    parser.add_argument('-l', '--loglevel',
                        help='Logging level. Default: %(default)s.',
                        choices=('debug', 'info', 'warning', 'error'),
                        default='warning')
    parser.add_argument('localfile',
                        help='The local file that you want to share',
                        type=argparse.FileType('r'))
    args = parse_args_and_apply_logging_level(parser, argv)
    jfs = JFS.JFS()
    jottadev = get_jotta_device(jfs)
    jottashare = jottadev.mountPoints['Shared']
    upload = jottashare.up(args.localfile)  # upload file
    public = upload.share() # share file
    logging.debug('Shared %r and got: %r (%s)', args.localfile, public, dir(public))
    for (filename, uuid, publicURI) in public.sharedFiles():
        print('%s is now available to the world at %s' % (filename, publicURI))
    return True # TODO: check return value of command


def ls(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='List files in Jotta folder.', add_help=False)
    parser.add_argument('-l', '--loglevel',
                        help='Logging level. Default: %(default)s.',
                        choices=('debug', 'info', 'warning', 'error'),
                        default='warning')
    parser.add_argument('-h', '--humanize', # this matches ls(1)
                        help='Print human-readable file sizes.',
                        action='store_true')
    parser.add_argument('-a',
                        '--all',
                        action='store_true',
                        help='Include deleted and incomplete files (otherwise ignored)')
    parser.add_argument('item',
                        nargs='?',
                        help='The file or directory to list. Defaults to the root dir',
                        type=commandline_text)
    parser.add_argument('-H', # because -h means --humanize
                        '--help',
                        help='Print this help',
                        action='help')
    args = parse_args_and_apply_logging_level(parser, argv)
    jfs = JFS.JFS()
    root_folder = get_root_dir(jfs)
    if args.item:
        if args.item.startswith('//'):
            # break out of root_folder
            item_path = posixpath.join(jfs.rootpath, args.item[1:])
        else:
            item_path = posixpath.join(root_folder.path, args.item)
        item = jfs.getObject(item_path)
    else:
        item = root_folder
    timestamp_width = 25
    logging.debug('about to ls %r', item)
    if isinstance(item, JFS.JFSFolder):
        files = [(
            f.created,
            print_size(f.size, humanize=args.humanize) if f.size else u'',
            u'D' if f.deleted else u'I' if f.state == 'INCOMPLETE' else u' ',
            f.name) for f in item.files() if not f.deleted and f.state != 'INCOMPLETE' or args.all]
        folders = [(u' '*timestamp_width, u'', u'D' if f.deleted else u' ', unicode(f.name))
                   for f in item.folders() if not f.deleted or args.all]
        widest_size = 0
        for f in files:
            if len(f[1]) > widest_size:
                widest_size = len(f[1])
        for item in sorted(files + folders, key=lambda t: t[3]):
            if args.all:
                print(u'%s %s %s %s' % (item[0], item[1].rjust(widest_size), item[2], item[3]))
            else:
                print(u'%s %s %s' % (item[0], item[1].rjust(widest_size), item[3]))
    else:
        print(' '.join([str(item.created), print_size(item.size, humanize=args.humanize), item.name]))
    return True # TODO: check return value of command


def download(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Download a file from Jottacloud.')
    parser.add_argument('remotefile',
                        help='The path to the file that you want to download',
                        type=commandline_text)
    parser.add_argument('-l', '--loglevel',
                        help='Logging level. Default: %(default)s.',
                        choices=('debug', 'info', 'warning', 'error'),
                        default='warning')
    args = parse_args_and_apply_logging_level(parser, argv)
    jfs = JFS.JFS()
    root_folder = get_root_dir(jfs)
    path_to_object = posixpath.join(root_folder.path, args.remotefile)
    remote_file = jfs.getObject(path_to_object)
    total_size = remote_file.size
    with open(remote_file.name, 'wb') as fh:
        bytes_read = 0
        with ProgressBar(expected_size=total_size) as bar:
            for chunk_num, chunk in enumerate(remote_file.stream()):
                fh.write(chunk)
                bytes_read += len(chunk)
                bar.show(bytes_read)
    print('%s downloaded successfully' % args.remotefile)
    return True # TODO: check/set return value


def mkdir(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Create a new folder in Jottacloud.')
    parser.add_argument('newdir',
                        help='The path to the folder that you want to create')
    parser.add_argument('-l', '--loglevel',
                        help='Logging level. Default: %(default)s.',
                        choices=('debug', 'info', 'warning', 'error'),
                        default='warning')
    args = parse_args_and_apply_logging_level(parser, argv)
    jfs = JFS.JFS()
    root_folder = get_root_dir(jfs)
    root_folder.mkdir(args.newdir)
    return True #  TODO: check return value of mkdir


def rm(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Delete an item from Jottacloud')
    parser.add_argument('file',
                        help='The path to the item that you want to delete')
    parser.add_argument('-l', '--loglevel',
                        help='Logging level. Default: %(default)s.',
                        choices=('debug', 'info', 'warning', 'error'),
                        default='warning')
    parser.add_argument('-f', '--force',
                        help='Completely deleted, no restore possiblity',
                        action='store_true')
    args = parse_args_and_apply_logging_level(parser, argv)
    jfs = JFS.JFS()
    root_dir = get_root_dir(jfs)
    item_path = posixpath.join(root_dir.path, args.file)
    item = jfs.getObject(item_path)
    if args.force:
        item.hard_delete()
    else:
        item.delete()
    print('%s deleted' % args.file)
    return True # TODO: check return value of command


def restore(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Restore a deleted item from Jottacloud')
    parser.add_argument('file',
                        type=commandline_text,
                        help='The path to the item that you want to restore')
    parser.add_argument('-l', '--loglevel',
                        help='Logging level. Default: %(default)s.',
                        choices=('debug', 'info', 'warning', 'error'),
                        default='warning')
    args = parse_args_and_apply_logging_level(parser, argv)
    jfs = JFS.JFS()
    root_dir = get_root_dir(jfs)
    item_path = posixpath.join(root_dir.path, args.file)
    item = jfs.getObject(item_path)
    item.restore()
    print('%s restored' % args.file)
    return True # TODO: check return value of command



def cat(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Display contents of a file from Jottacloud')
    parser.add_argument('file',
                        type=commandline_text,
                        help='The path to the file that you want to show')
    parser.add_argument('-l', '--loglevel',
                        help='Logging level. Default: %(default)s.',
                        choices=('debug', 'info', 'warning', 'error'),
                        default='warning')
    args = parse_args_and_apply_logging_level(parser, argv)
    jfs = JFS.JFS()
    if args.file.startswith('//'):
        # break out of root_folder
        item_path = posixpath.join(jfs.rootpath, args.file[1:])
    else:
        root_dir = get_root_dir(jfs)
        item_path = posixpath.join(root_dir.path, args.file)
    item = jfs.getObject(item_path)
    if not isinstance(item, JFS.JFSFile):
        print("%r is not a file (it's a %s), so we can't show it" % (args.file, type(item)))
        sys.exit(1)
    s = ''
    for chunk in item.stream():
        print(chunk.encode(sys.getdefaultencoding()))
        s = s + chunk
    return s


def scanner(argv=None):

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description=__doc__,
                                    epilog="""The program expects to find an entry for "jottacloud.com" in your .netrc,
                                    or JOTTACLOUD_USERNAME and JOTTACLOUD_PASSWORD in the running environment.
                                    This is not an official JottaCloud project.""")
    parser.add_argument('-l', '--loglevel',
                        help='Logging level. Default: %(default)s.',
                        choices=('debug', 'info', 'warning', 'error'),
                        default='warning')
    parser.add_argument('--errorfile',
                        type=commandline_text,
                        help='A file to write errors to',
                        default='./jottacloudclient.log')
    parser.add_argument('--exclude',
                        type=re.compile,
                        action='append',
                        help='Exclude paths matched by this pattern (can be repeated)')
    parser.add_argument('--prune-files', dest='prune_files',
                        help='Delete files that does not exist locally',
                        action='store_true')
    parser.add_argument('--prune-folders',
                        dest='prune_folders',
                        help='Delete folders that does not exist locally',
                        action='store_true')
    parser.add_argument('--prune-all',
                        dest='prune_all',
                        help='Combines --prune-files  and --prune-folders',
                        action='store_true')
    parser.add_argument('--version',
                        action='version',
                        version=__version__)
    parser.add_argument('--dry-run',
                        action='store_true',
                        help="don't actually do any uploads or deletes, just show what would be done")
    parser.add_argument('topdir',
                        type=is_dir,
                        help='Path to local dir that needs syncing')
    parser.add_argument('jottapath',
                        type=commandline_text,
                        help='The path at JottaCloud where the tree shall be synced (must exist)')
    args = parse_args_and_apply_logging_level(parser, argv)
    if args.prune_all:
        args.prune_files = True
        args.prune_folders = True

    fh = logging.FileHandler(args.errorfile)
    fh.setLevel(logging.ERROR)
    logging.getLogger('').addHandler(fh)

    jfs = JFS.JFS()

    logging.info('args: topdir %r, jottapath %r', args.topdir, args.jottapath)
    filescanner(args.topdir, args.jottapath, jfs, args.errorfile, args.exclude, args.dry_run, args.prune_files, args.prune_folders)


def monitor(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if not HAS_WATCHDOG:
        message = ['jotta-monitor requires watchdog (pip install watchdog), install that and try again.']
        print(' '.join(message))
        sys.exit(1)

    # Has watchdog, can safely import filemonitor
    from .monitor import filemonitor

    parser = argparse.ArgumentParser(description=__doc__,
                                    epilog="""The program expects to find an entry for "jottacloud.com" in your .netrc,
                                    or JOTTACLOUD_USERNAME and JOTTACLOUD_PASSWORD in the running environment.
                                    This is not an official JottaCloud project.""")
    parser.add_argument('-l', '--loglevel',
                        help='Logging level. Default: %(default)s.',
                        choices=('debug', 'info', 'warning', 'error'),
                        default='warning')
    parser.add_argument('--errorfile',
                        help='A file to write errors to',
                        default='./jottacloudclient.log')
    parser.add_argument('--version',
                        action='version',
                        version=__version__)
    parser.add_argument('--dry-run',
                        action='store_true',
                        help="don't actually do any uploads or deletes, just show what would be done")
    parser.add_argument('topdir',
                        type=is_dir,
                        help='Path to local dir that needs syncing')
    parser.add_argument('mode',
                        type=commandline_text,
                        help='Mode of operation: ARCHIVE, SYNC or SHARE. See README.md',
                        choices=( 'archive', 'sync', 'share') )
    args = parse_args_and_apply_logging_level(parser, argv)
    fh = logging.FileHandler(args.errorfile)
    fh.setLevel(logging.ERROR)
    logging.getLogger('').addHandler(fh)

    jfs = JFS.JFS()

    filemonitor(args.topdir, args.mode, jfs)
