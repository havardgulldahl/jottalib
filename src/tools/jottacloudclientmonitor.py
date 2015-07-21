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

import time, os, os.path, sys, logging, argparse, netrc

from watchdog.observers import Observer # pip install watchdog
from watchdog.events import LoggingEventHandler, FileSystemEventHandler

from clint.textui import progress, puts, colored

sys.path.insert(0, '..')
from jottalib.JFS import JFS
from jottacloudclient import jottacloud, __version__




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
    '''Handles Archive events:
    
    new file: upload to cloud and delete locally
    '''
    mode = 'Archive'
    
    def __init__(self, jfs, topdir, jottaroot=None):
        self.jfs = jfs
        self.topdir = topdir
        self.jottaroot = jottaroot and jottaroot or ('/Jotta/%s' % self.mode)
        
    def get_jottapath(self, p):
        rel = os.path.relpath(p, self.topdir) # strip leading path
        parts = [self.jottaroot, ] + list(os.path.split(rel)) # explode path to normalize OS path separators
        return '/'.join( parts ).replace('//', '/') # return url
    
    def on_modified(self, event):
        'Called when a file is modified. '
        logging.info('Modified file detectd: %s', event.src_path)
        try:
            open(event.src_path)
        except IOError: # file is not finished 
            logging.info('File is not finished')
            return 
        if event.is_directory:
            jottacloud.mkdir(event.src_path, self.jfs)
        else:
            logging.info('Uploading file %s to %s', event.src_path, self.get_jottapath(event.src_path))
            #jottacloud.new(event.src_path, self.get_jottapath(event.src_path), self.jfs)
            #os.remove(event.src_path)
    
class ShareEventHandler(FileSystemEventHandler):
    '''Handles Share events:
    
    new file: upload to cloud and replace contents with public share url
    delete file: delete from cloud
    '''
    pass
    
class SyncEventHandler(FileSystemEventHandler):
    '''Handles Sync events:
    
    new file: upload it to the cloud
    file is renamed: rename it in the cloud
    file is changed: upload the new file
    file is deleted: delete it from the cloud
    '''
    pass

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
    parser.add_argument('mode', help='Mode of operation: ARCHIVE, SYNC or SHARE. See README.md', 
                        choices=( 'archive', 'sync', 'share') )
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
            logging.exception('SAFERUN: Got exception when processing %s', args)
            errors.update( {args[0]:e} )
            return False

    event_handler = ArchiveEventHandler(jfs, args.topdir)
    #event_handler = LoggingEventHandler()
    observer = Observer()
    observer.schedule(event_handler, args.topdir, recursive=True)
    observer.start()
    try:
        puts(colored.green('Starting JottaCloud monitor'))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        puts(colored.red('JottaCloud monitor stopped'))
    observer.join()