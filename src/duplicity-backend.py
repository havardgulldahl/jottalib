# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
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

import os.path
import string
import urllib

import duplicity.backend
from duplicity.errors import BackendException


class JottaCloudBackend(duplicity.backend.Backend):
    """Connect to remote store using JottaCloud API"""

    def __init__(self, parsed_url):
        duplicity.backend.Backend.__init__(self, parsed_url)

        # Import JottaCloud libraries.
        try:
            import jottalib
        except ImportError:
            raise BackendException('JottaCloud backend requires jottalib' 
                                   ' (see https://pypi.python.org/pypi/jottalib).')

        # Setup client instance.
        self.client = jottalib.JFS.JFS(parsed_url.username, self.get_password())
        #self.client.http_client.debug = False

        # Fetch destination folder entry (and create hierarchy if required).
        jottadev = None
        for j in jfs.devices: # find Jotta/Backup folder
            if j.name == 'Jotta':
                jottadev = j      
        try:
            self.folder = jottadev.mountPoints['Backup']
        except IndexError:
            try:
                self.folder = jottadev.mkdir('Backup')  
            except:
                raise BackendException("Error while creating destination folder 'Backup')")
        except:
            raise BackendException("Error while fetching destination folder 'Backup')")

    @command()
    def _put(self, source_path, remote_filename):
        remote_dir  = urllib.unquote(self.parsed_url.path.lstrip('/'))
        remote_path = os.path.join(self.folder.path, remote_dir, remote_filename).rstrip()
        from_file = open(source_path.name, "rb")
        resp = self.client.put(remote_path, from_file)
        log.Debug( 'jottacloud.put(%s,%s): %s'%(source_path.name, remote_path, resp))

    @command()
    def _get(self, remote_filename, local_path):
        remote_path = os.path.join(self.folder.path, 
                                   urllib.unquote(self.parsed_url.path), 
                                   remote_filename).rstrip()

        to_file = open( local_path.name, 'wb' )
        f = self.client.get(remote_path)
        log.Debug('jottacloud.get(%s,%s): %s'%(remote_path,local_path.name, f))
        to_file.write(f.read())
        f.close()
        to_file.close()

        local_path.setdata()

    @command()
    def _list(self):
        # Do a long listing to avoid connection reset
        remote_dir = os.path.join(self.folder.path,
                                  urllib.unquote(self.parsed_url.path.lstrip('/')).rstrip()
                                  )
        folder = self.client.get(remote_dir)
        log.Debug('jottacloud.list(%s): %s'%(remote_dir,folder))
        return list(folder.files())

    @command()
    def _delete(self, filename):
        remote_dir = urllib.unquote(self.parsed_url.path.lstrip('/')).rstrip()
        remote_name = os.path.join(self.folder.path, remote_dir, filename )
        #first, get file object
        f = self.client.get(remote_name)
        # now, delete it
        resp = f.delete()
        log.Debug('jottacloud.delete(%s): %s'%(remote_name,resp))

    # @command()
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

duplicity.backend.register_backend("jottacloud", JottaCloudBackend)