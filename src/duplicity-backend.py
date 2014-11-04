# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4; encoding:utf-8 -*-
#
# Copyright 2014 Håvard Gulldahl
#
# in part based on dpbxbackend.py:
# Copyright 2013 jno <jno@pisem.net>
#
# This file is part of duplicity.
#
# Duplicity is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# Duplicity is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with duplicity; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

# stdlib
import os, os.path
import string
import urllib, locale

# import duplicity stuff # version 0.6
import duplicity.backend
from duplicity.backend import retry
from duplicity import log
from duplicity.errors import *

class JottaCloudBackend(duplicity.backend.Backend):
    """Connect to remote store using JottaCloud API"""

    def __init__(self, parsed_url):
        duplicity.backend.Backend.__init__(self, parsed_url)

        # Import JottaCloud libraries.
        try:
            from jottalib import JFS
        except ImportError:
            raise
            raise BackendException('JottaCloud backend requires jottalib' 
                                   ' (see https://pypi.python.org/pypi/jottalib).')

        # Setup client instance.
        _pass = os.environ.get('JOTTACLOUD_PASSWORD', None)
        if _pass is None:
            _pass = self.get_password()
        self.client = JFS.JFS(parsed_url.username, _pass)
        #self.client.http_client.debug = False

        # Fetch destination folder entry (and create hierarchy if required).
        try:
            self.folder = self.client.getObject('%s/backup' % parsed_url.path)
        except JFS.JFSNotFoundError:
            parentfolder = self.client.getObject(parsed_url.path)
            try:
                self.folder = parentfolder.mkdir('backup')
            except:
                raise
                raise BackendException("Error while creating destination folder 'Backup')")
        except:
            raise

    @retry
    def put(self, source_path, remote_filename=None, raise_errors=False):
        """Transfer source_path to remote_filename"""
        # Default remote file name.
        if not remote_filename:
            remote_filename = os.path.basename(source_path.get_filename())

        resp = self.folder.up(source_path.open(), remote_filename)
        log.Debug( 'jottacloud.put(%s,%s): %s'%(source_path.name, remote_filename, resp))

    @retry
    def get(self, remote_filename, local_path, raise_errors=False):
        print "YYYYYYYYY %s" % os.path.join(self.folder.path, remote_filename)
        to_file = open( local_path.name, 'wb' )
        f = self.client.getObject(os.path.join(self.folder.path, remote_filename))
        log.Debug('jottacloud.get(%s,%s): %s'%(remote_filename,local_path.name, f))
        to_file.write(f.read())
        to_file.close()

    @retry
    def list(self, raise_errors=False):
        log.Debug('jottacloud.list raise e %s'%(raise_errors))
        log.Debug('jottacloud.list: %s'%(self.folder.files()))
        encoding = locale.getdefaultlocale()[1]
        if encoding is None:
            encoding = 'LATIN1'
        return list([f.name.encode(encoding) for f in self.folder.files() if not f.is_deleted()])

    @retry
    def delete(self, filenames, raise_errors=False):
        log.Debug('jottacloud.delete: %s'%filenames)
        for filename in filenames:
            remote_name = os.path.join(self.folder.path, filename )
            #first, get file object
            f = self.client.getObject(remote_name)
            log.Debug('jottacloud.delete deleting: %s (%s)'%(f, type(f)))
            # now, delete it
            resp = f.delete()
            log.Debug('jottacloud.delete(%s): %s'%(remote_name,resp))

    # @retry
    # def _close(self):
    #     """close backend session? no! just "flush" the data"""
    #     info = self.api_client.account_info()
    #     log.Debug('dpbx.close():')
    #     for k in info :
    #         log.Debug(':: %s=[%s]' % (k, info[k]))
    #     entries = []
    #     more = True
    #     cursor = None
    #     while more :
    #         info = self.api_client.delta(cursor)
    #         if info.get('reset', False) :
    #             log.Debug("delta returned True value for \"reset\", no matter")
    #         cursor = info.get('cursor', None)
    #         more = info.get('more', False)
    #         entr = info.get('entries', [])
    #         entries += entr
    #     for path, meta in entries:
    #         mm = meta and 'ok' or 'DELETE'
    #         log.Info(':: :: [%s] %s' % (path, mm))
    #         if meta :
    #             for k in meta :
    #                 log.Debug(':: :: :: %s=[%s]' % (k, meta[k]))

    def _mkdir(self, path):
        """create a new directory"""
        resp = self.client.file_create_folder(path)
        log.Debug('jottacloud._mkdir(%s): %s'%(path,resp))

duplicity.backend.register_backend("jotta", JottaCloudBackend)

