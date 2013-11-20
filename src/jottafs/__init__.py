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
# Copyright 2011,2013 Håvard Gulldahl <havard@gulldahl.no>


# importing stdlib
import sys, os
import urllib, logging, datetime


# importing external dependencies (pip these, please!)
import requests
import lxml, lxml.objectify
import dateutil, dateutil.parser

JFS_ROOT='https://www.jotta.no/jfs/'

class JFSError(Exception):
    pass

class JFSDevice(object):
    'OO interface to a device, for convenient access. Type less, do more.'
    def __init__(self, deviceobject, jfs): # deviceobject from lxml.objectify
        self.dev = deviceobject
        self.__jfs = jfs

    def contents(self, path=None):
        c = self.__jfs.get('/' + self.name + path or '/')
        print c

    @property
    def modified(self):
        return dateutil.parser.parse(str(self.dev.modified))

    @property
    def name(self):
        return unicode(self.dev.name)

    @property
    def type(self):
        return unicode(self.dev.type)

    @property
    def size(self):
        return int(self.dev.size, 10)

    @property
    def sid(self):
        return str(self.dev.sid)


class JFS(object):
    def __init__(self, username, password):
        from requests.auth import HTTPBasicAuth
        self.auth = HTTPBasicAuth(username, password)
        self.root = JFS_ROOT + username
        self.fs = self.get(self.root)

    def get(self, url):
        ident = 'jottafs-a-fuse-filesystem/0.1'
        if not url.startswith('http'):
            # relative url
            url = self.root + url
        r = requests.get(url, auth=self.auth)
        if r.status_code in ( 500, ):
            raise JFSError(r.reason)
        return lxml.objectify.fromstring(r.content)

    # property overloading
    @property
    def devices(self):
        'return generator of configured devices'
        return self.fs is not None and [JFSDevice(d, self) for d in self.fs.devices.iterchildren()] or [x for x in []]

    @property
    def locked(self):
        'return bool'
        return self.fs is not None and self.fs.locked or None

    @property
    def read_locked(self):
        'return bool'
        return self.fs is not None and self.fs['read-locked'] or None

    @property
    def write_locked(self):
        'return bool'
        return self.fs is not None and self.fs['write-locked'] or None

    @property
    def capacity(self):
        'return int of storage capacity in bytes'
        return self.fs is not None and self.fs.capacity or -1

    @property
    def usage(self):
        'return int of storage usage in bytes'
        return self.fs is not None and self.fs.usage or -1


if __name__=='__main__':
    jfs = JFS(os.environ['JOTTACLOUD_USERNAME'], password=os.environ['JOTTACLOUD_PASSWORD'])
    from pprint import pprint
    print lxml.objectify.dump(jfs.fs)

