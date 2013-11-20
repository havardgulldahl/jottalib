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

# metadata

__author__ = 'havard@gulldahl.no'
__version__ = '0.1'

# importing stdlib
import sys, os
import urllib, logging, datetime

# importing external dependencies (pip these, please!)
import requests
import lxml, lxml.objectify
import dateutil, dateutil.parser

# some setup
JFS_ROOT='https://www.jotta.no/jfs/'
logging.basicConfig(level=logging.INFO)

class JFSError(Exception):
    pass

class JFSFile(object):
    'OO interface to a file, for convenient access. Type less, do more.'
    def __init__(self, fileobject, mountPoint, jfsdevice): # fileobject from lxml.objectify
        self.f = fileobject
        self.mountPoint = mountPoint
        self.device = jfsdevice
        lxml.objectify.dump(fileobject)

    def stream(self):
        'get the file contents'
        self.device._jfs.get('%s?mode=bin' % self.path)
        """
            * name = 'jottacloud.sync.pdfname'
            * uuid = '37530f11-d55b-4f31-acf4-27854813cd34'
            currentRevision = None [ObjectifiedElement]
                number = 1 [IntElement]
                state = 'COMPLETED' [StringElement]
                created = '2010-11-19-T12:34:18Z' [StringElement]
                modified = '2010-11-19-T12:34:18Z' [StringElement]
                mime = 'image/jpeg' [StringElement]
                mstyle = 'IMAGE_JPEG' [StringElement]
                size = 125848 [IntElement]
                md5 = 'a0dc8233169b238681c43f9981efe8e1' [StringElement]
                updated = '2010-11-19-T12:34:28Z' [StringElement]
        """

    @property
    def name(self):
        return unicode(self.f.attrib['name'])

    @property
    def path(self):
        return '/'.join( (unicode(self.device.name), unicode(self.mountPoint.name), self.name) )

    @property
    def revisionNumber(self):
        return int(self.f.currentRevision.number)
    
    @property
    def created(self):
        return dateutil.parser.parse(str(self.f.currentRevision.created))

    @property
    def modified(self):
        return dateutil.parser.parse(str(self.f.currentRevision.modified))

    @property
    def updated(self):
        return dateutil.parser.parse(str(self.f.currentRevision.updated))

    @property
    def size(self):
        return int(self.f.currentRevision.size)
    
    @property
    def md5(self):
        return str(self.f.currentRevision.md5)
    
    @property
    def mime(self):
        return unicode(self.f.currentRevision.mime)
    
    @property
    def state(self):
        return unicode(self.f.currentRevision.state)
    

class JFSDevice(object):
    'OO interface to a device, for convenient access. Type less, do more.'
    def __init__(self, deviceobject, jfs): # deviceobject from lxml.objectify
        self.dev = deviceobject
        self._jfs = jfs
        self.mountPoints = {mp.name:mp for mp in self.contents().mountPoints.iterchildren()}

    def contents(self, path=None):
        if isinstance(path, lxml.objectify.ObjectifiedElement) and hasattr(path, 'name'):
            # passed an object, use .'name' as path value
            path = '/%s' % path.name
        c = self._jfs.get('/%s%s' % (self.name, path or '/'))
        return c

    def files(self, mountPoint):
        """Get an iterator of JFSFile() from the given mountPoint. 
        
        "mountPoint" may be either an actual mountPoint element from JFSDevice.mountPoints{} or its .name. """
        if isinstance(mountPoint, basestring):
            # shortcut: pass a mountpoint name
            mountPoint = self.mountPoints[mountPoint]
        try:
            return [JFSFile(f, mountPoint, self) for f in self.contents(mountPoint).files.iterchildren()]
        except AttributeError as err:
            # no files at all 
            return [x for x in []]

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
        return int(self.dev.size)

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
        headers  = {'User-Agent':'JottaFS %s (https://git.gitorious.org/jottafs/jottafs.git)' % (__version__, ),
                    'From': __author__}
        if not url.startswith('http'):
            # relative url
            url = self.root + url
        logging.info("getting url: %s" % url)
        r = requests.get(url, headers=headers, auth=self.auth)
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
        return self.fs is not None and bool(self.fs.locked) or None

    @property
    def read_locked(self):
        'return bool'
        return self.fs is not None and bool(self.fs['read-locked']) or None

    @property
    def write_locked(self):
        'return bool'
        return self.fs is not None and bool(self.fs['write-locked']) or None

    @property
    def capacity(self):
        'return int of storage capacity in bytes'
        return self.fs is not None and int(self.fs.capacity) or -1

    @property
    def usage(self):
        'return int of storage usage in bytes'
        return self.fs is not None and int(self.fs.usage) or -1


if __name__=='__main__':
    jfs = JFS(os.environ['JOTTACLOUD_USERNAME'], password=os.environ['JOTTACLOUD_PASSWORD'])
    from pprint import pprint
    print lxml.objectify.dump(jfs.fs)
    x = list(jfs.devices)[2]
    #print lxml.objectify.dump(x.contents(x.mountPoints['Sync']))
    files = x.files('Sync')


