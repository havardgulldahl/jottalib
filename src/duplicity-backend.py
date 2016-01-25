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
import os
import os.path
import posixpath
import locale

# import duplicity stuff # version 0.6
import duplicity.backend
from duplicity import log
from duplicity.errors import *

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
        username = parsed_url.username or os.environ.get('JOTTACLOUD_USERNAME')
        self.client = JFS.JFS(auth=(username, _pass))
        #self.client.http_client.debug = False
        root_dir = get_root_dir(self.client)

        # Fetch destination folder entry (and create hierarchy if required).
        path = posixpath.join(root_dir.path, parsed_url.path.lstrip('/'))
        try:
        #    self.folder = root_dir#self.client.getObject('%s/duplicity' % parsed_url.path.lstrip('//'))
            self.folder = self.client.getObject(path)
        except JFS.JFSNotFoundError:
            try:
                self.folder = root_dir.mkdir(parsed_url.path.lstrip('/'))
            except:
                raise
                raise BackendException("Error while creating destination folder 'Backup')")
        except:
            raise

    def _put(self, source_path, remote_filename=None, raise_errors=False):
        """Transfer source_path to remote_filename"""
        # Default remote file name.
        if not remote_filename:
            remote_filename = os.path.basename(source_path.get_filename())

        resp = self.folder.up(source_path.open(), remote_filename)
        log.Debug( 'jottacloud.put(%s,%s): %s'%(source_path.name, remote_filename, resp))

    def _get(self, remote_filename, local_path, raise_errors=False):
        remote_file = self.client.getObject(posixpath.join(self.folder.path, remote_filename))
        log.Debug('jottacloud.get(%s,%s): %s' % (remote_filename, local_path.name, remote_file))
        with open(local_path.name, 'wb') as to_file:
            for chunk in remote_file.stream():
                to_file.write(chunk)

    def _list(self, raise_errors=False):
        log.Debug('jottacloud.list raise e %s'%(raise_errors))
        log.Debug('jottacloud.list: %s'%(self.folder.files()))
        encoding = locale.getdefaultlocale()[1]
        if encoding is None:
            encoding = 'LATIN1'
        return list([f.name.encode(encoding) for f in self.folder.files()
                     if not f.is_deleted() and f.state != 'INCOMPLETE'])

    def _delete(self, filename, raise_errors=False):
        log.Debug('jottacloud.delete: %s'%filename)
        remote_name = os.path.join(self.folder.path, filename)
        #first, get file object
        f = self.client.getObject(remote_name)
        log.Debug('jottacloud.delete deleting: %s (%s)'%(f, type(f)))
        # now, delete it
        resp = f.delete()
        log.Debug('jottacloud.delete(%s): %s'%(remote_name,resp))
        self.folder.sync()


duplicity.backend.register_backend("jotta", JottaCloudBackend)
