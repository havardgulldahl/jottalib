# -*- encoding: utf-8 -*-
#
# Copyright 2014 Håvard Gulldahl <havard@gulldahl.no>
#
# This file is part of duplicity.
# This is a backup backend to store files with the Norwegian backup 
# system JottaCloud.
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

import os

import duplicity.backend
from duplicity.errors import BackendException
from duplicity import log
from duplicity import globals

class JottaCloudBackend(duplicity.backend.Backend):
    def __init__(self, parsed_url):
        duplicity.backend.Backend.__init__(self, parsed_url)
        self.username = parsed_url.hostname
        self.path = parsed_url.path

    def put(self, source_path, remote_filename = None):
        """Copy file to remote"""
        if not remote_filename:
            remote_filename = source_path.get_filename()
        remote_full = self.meta_base + self.quote(remote_filename)
        # check if it exists already, returns existing content_path
        resp, content = self.client.request(remote_full,ignore=[404])
        if resp['status']=='404':
            # put with path returns new content_path
            resp, content = self.client.request(remote_full,
                                                method="PUT",
                                                headers = { 'content-type': 'application/json' },
                                                body=dumps({"kind":"file"}))
        elif resp['status']!='200':
            raise BackendException("access to %s failed, code %s" % (remote_filename, resp['status']))

        assert(content['content_path'] is not None)
        # content_path allows put of the actual material
        remote_full = self.content_base + self.quote(content['content_path'])
        log.Info("uploading file %s to location %s" % (remote_filename, remote_full))

        size = os.path.getsize(source_path.name)
        fh=open(source_path.name,'rb')

        content_type = 'application/octet-stream'
        headers = {"Content-Length": str(size),
                   "Content-Type": content_type}
        resp, content = self.client.request(remote_full,
                                            method="PUT",
                                            body=fh,
                                            headers=headers)
        fh.close()

    def get(self, filename, local_path):
        """Get file and put in local_path (Path object)"""

        # get with path returns content_path
        remote_full = self.meta_base + self.quote(filename)
        resp, content = self.client.request(remote_full)

        assert(content['content_path'] is not None)
        # now we have content_path to access the actual material
        remote_full = self.content_base + self.quote(content['content_path'])
        log.Info("retrieving file %s from location %s" % (filename, remote_full))
        resp, content = self.client.request(remote_full)

        f = open(local_path.name, 'wb')
        f.write(content)
        f.close()
        local_path.setdata()

    def list(self):
        """List files in that directory"""
        remote_full = self.meta_base + "?include_children=true"
        resp, content = self.client.request(remote_full)

        filelist = []
        if 'children' in content:
            for child in content['children']:
                path = urllib.unquote(child['path'].lstrip('/'))
                filelist += [path.encode('utf-8')]
        return filelist

    def delete(self, filename_list):
        """Delete all files in filename list"""
        import types
        assert type(filename_list) is not types.StringType

        for filename in filename_list:
            remote_full = self.meta_base + self.quote(filename)
            resp, content = self.client.request(remote_full,method="DELETE")

    def _query_file_info(self, filename):
        """Query attributes on filename"""
        remote_full = self.meta_base + self.quote(filename)
        resp, content = self.client.request(remote_full)

        size = content['size']
        return {'size': size}

duplicity.backend.register_backend("jottacloud", U1Backend)

