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
# Copyright 2011,2013,2014 Håvard Gulldahl <havard@gulldahl.no>

# metadata

__author__ = 'havard@gulldahl.no'
from jottalib import __version__

# importing stdlib
import sys, os, os.path, time
import urllib, logging, datetime, hashlib
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# importing external dependencies (pip these, please!)
import requests
import requests_cache
requests_cache.core.install_cache(backend='memory', expire_after=30.0, fast_save=True)
import lxml, lxml.objectify
import dateutil, dateutil.parser

#monkeypatch urllib3 param function to bypass bug in jottacloud servers
from requests.packages import urllib3
urllib3.fields.format_header_param_orig = urllib3.fields.format_header_param
def mp(name, value):
    return urllib3.fields.format_header_param_orig(name, value).replace('filename*=', 'filename=')
urllib3.fields.format_header_param = mp



# some setup
JFS_ROOT='https://www.jotta.no/jfs/'
JFS_CACHELIMIT=1024*1024 # stuff below this threshold (in bytes) will be cached

class JFSError(Exception):
    @staticmethod
    def raiseError(e, path): # parse object from lxml.objectify and
        if(e.code) == 404:
            raise JFSNotFoundError('%s does not exist (%s)' % (path, e.message))
        elif(e.code) == 401:
            raise JFSCredentialsError("Your credentials don't match for %s (%s) (probably incorrect password!)" % (path, e.message))
        elif(e.code) == 403:
            raise JFSAuthenticationError("You don't have access to %s (%s)" % (path, e.message))
        elif(e.code) == 500:
            raise JFSServerError("Internal server error: %s (%s)" % (path, e.message))
        elif(e.code) == 400:
            raise JFSBadRequestError('Bad request: %s (%s)' % (path, e.message))
        else:
            raise JFSError('Error accessing %s (%s)' % (path, e.message))

class JFSBadRequestError(JFSError): # HTTP 400
    pass

class JFSCredentialsError(JFSError): # HTTP 401
    pass

class JFSNotFoundError(JFSError): # HTTP 404
    pass

class JFSAccessError(JFSError): #
    pass

class JFSAuthenticationError(JFSError): # HTTP 403
    pass

class JFSServerError(JFSError): # HTTP 500
    pass

class JFSFolder(object):
    'OO interface to a folder, for convenient access. Type less, do more.'
    def __init__(self, folderobject, jfs, parentpath): # folderobject from lxml.objectify
        self.folder = folderobject
        self.parentPath = parentpath
        self.jfs = jfs
        self.synced = False

    @property
    def name(self):
        return self.folder.attrib.has_key('name') and unicode(self.folder.attrib['name']) or unicode(self.folder.name)
        return unicode(self.folder.attrib.get('name', self.folder.name))

    @property
    def path(self):
        return '%s/%s' % (self.parentPath, self.name)

    @property
    def deleted(self):
        'Return datetime.datetime or None if the file isnt deleted'
        _d = self.folder.attrib.get('deleted', None)
        if _d is None: return None
        return dateutil.parser.parse(str(_d))

    def sync(self):
        'Update state of folder from Jottacloud server'
        logging.info("syncing %s" % self.path)
        self.folder = self.jfs.get(self.path)
        self.synced = True

    def is_deleted(self):
        'Return bool based on self.deleted'
        return self.deleted is not None

    def files(self):
        if not self.synced:
            self.sync()
        try:
            return [JFSFile(f, self.jfs, self.path) for f in self.folder.files.iterchildren()]
        except AttributeError:
            return [x for x in []]

    def folders(self):
        if not self.synced:
            self.sync()
        try:
            return [JFSFolder(f, self.jfs, self.path) for f in self.folder.folders.iterchildren()]
        except AttributeError:
            return [x for x in []]

    def mkdir(self, foldername):
        'Create a new subfolder and return the new JFSFolder'
        url = '%s?mkDir=true' % os.path.join(self.path, foldername)
        r = self.jfs.post(url)
        self.sync()
        return r

    def delete(self):
        'Delete this folder and return a deleted JFSFolder'
        url = '%s?dlDir=true' % self.path
        r = self.jfs.post(url)
        self.sync()
        return r

    def rename(self, newpath):
        "Move folder to a new name, possibly a whole new path"
        # POST https://www.jottacloud.com/jfs/**USERNAME**/Jotta/Sync/Ny%20mappe?mvDir=/**USERNAME**/Jotta/Sync/testFolder
        url = '%s?mvDir=/%s%s' % (self.path, self.jfs.username, newpath)
        r = self.jfs.post(url, extra_headers={'Content-Type':'application/octet-stream'})
        return r

    def up(self, fileobj_or_path, filename=None):
        'Upload a file to current folder and return the new JFSFile'
        if not isinstance(fileobj_or_path, file):
            filename = os.path.basename(fileobj_or_path)
            fileobj_or_path = open(fileobj_or_path, 'rb')
        logging.debug('.up %s ->  %s %s', repr(fileobj_or_path), repr(self.path), repr(filename))
        r = self.jfs.up(os.path.join(self.path, filename), fileobj_or_path)
        self.sync()
        return r

class JFSIncompleteFile(object):
    'OO interface to an incomplete file.'
    """<file name="h2.jpg" uuid="d492d1fb-6dd4-4ce3-9ab6-e5369ac8abf1" time="2014-12-11-T22:25:04Z" host="dn-092.site-000.jotta.no">
<path xml:space="preserve">/havardgulldahl/gulldahlpc/B/teste/jottatest</path>
<abspath xml:space="preserve">/havardgulldahl/gulldahlpc/B/teste/jottatest</abspath>
<latestRevision>
<number>1</number>
<state>INCOMPLETE</state>
<created>2014-12-11-T21:45:13Z</created>
<modified>2014-12-11-T21:45:13Z</modified>
<mime>image/jpeg</mime>
<mstyle>IMAGE_JPEG</mstyle>
<md5>25bf47bf6fa3b11b9b920887fb19f717</md5>
<updated>2014-12-11-T21:45:13Z</updated>
</latestRevision>
</file>"""
    def __init__(self, fileobject, jfs, parentpath): # fileobject from lxml.objectify
        self.f = fileobject
        self.jfs = jfs
        self.parentPath = parentpath

    def resume(self, fileobj_or_path):
        raise NotImplementedError

    def is_image(self):
        'Return bool based on self.mime'
        return os.path.dirname(self.mime) == 'image'

    @property
    def name(self):
        return unicode(self.f.attrib['name'])

    @property
    def uuid(self):
        return unicode(self.f.attrib['uuid'])

    @property
    def deleted(self):
        'Return datetime.datetime or None if the file isnt deleted'
        _d = self.f.attrib.get('deleted', None)
        if _d is None: return None
        return dateutil.parser.parse(str(_d))

    @property
    def path(self):
        return '%s/%s' % (self.parentPath, self.name)

    @property
    def revisionNumber(self):
        'return int of current revision'
        return int(self.f.latestRevision.number)

    @property
    def created(self):
        'return datetime.datetime'
        return dateutil.parser.parse(str(self.f.latestRevision.created))

    @property
    def modified(self):
        'return datetime.datetime'
        return dateutil.parser.parse(str(self.f.latestRevision.modified))

    @property
    def updated(self):
        'return datetime.datetime'
        return dateutil.parser.parse(str(self.f.latestRevision.updated))

    @property
    def md5(self):
        return str(self.f.latestRevision.md5)

    @property
    def mime(self):
        return unicode(self.f.latestRevision.mime)

    @property
    def state(self):
        return unicode(self.f.latestRevision.state)

class JFSFile(JFSIncompleteFile):
    'OO interface to a file, for convenient access. Type less, do more.'
    ## TODO: add <revisions> iterator for all
    """
<file name="jottacloud.sync.pdfname" uuid="37530f11-d55b-4f31-acf4-27854813cd34" time="2013-12-15-T01:11:52Z" host="dn-029.site-000.jotta.no">
  <path xml:space="preserve">/havardgulldahl/Jotta/Sync</path>
  <abspath xml:space="preserve">/havardgulldahl/Jotta/Sync</abspath>
  <currentRevision>
    <number>1</number>
    <state>COMPLETED</state>
    <created>2013-07-19-T22:59:16Z</created>
    <modified>2013-07-19-T22:59:17Z</modified>
    <mime>application/octet-stream</mime>
    <mstyle>APPLICATION_OCTET_STREAM</mstyle>
    <size>218028</size>
    <md5>e8f05ca4ebd70bc93ce2f18e26cee2a3</md5>
    <updated>2013-07-19-T22:59:31Z</updated>
  </currentRevision>
</file>

    """
    BIGTHUMB=1
    MEDIUMTHUMB=2
    SMALLTHUMB=3

    def __init__(self, fileobject, jfs, parentpath): # fileobject from lxml.objectify
        self.f = fileobject
        self.jfs = jfs
        self.parentPath = parentpath

    def stream(self, chunkSize=1024):
        'Returns a generator to iterate over the file contents'
        return self.jfs.stream(url='%s?mode=bin' % self.path, chunkSize=chunkSize)

    def read(self):
        'Get the file contents as string'
        return self.jfs.raw('%s?mode=bin' % self.path, usecache=self.size < JFS_CACHELIMIT) # dont cache large files
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

    def readpartial(self, start, end):
        'Get a part of the file, from start byte to end byte (integers)'
        return self.jfs.raw('%s?mode=bin' % self.path,
                            usecache=False,
                            extra_headers={'Range':'bytes=%s-%s' % (start, end)})

    def write(self, data):
        'Put, possibly replace, file contents with (new) data'
#         return self.jfs.post(self.path, content=data,
#                              extra_headers={'Content-Type':'application/octet-stream'})
        if not hasattr(data, 'read'):
            data = StringIO(data)
        self.jfs.up(self.path, data)

    def share(self):
        'Enable public access at secret, share only uri, and return that uri'
        url = 'https://www.jottacloud.com/rest/webrest/%s/action/enableSharing' % self.jfs.username
        data = {'paths[]':self.path.replace(u'https://www.jotta.no/jfs', ''),
                'web':'true',
                'ts':int(time.time()),
                'authToken':0}
        r = self.jfs.post(url, content=data)
        return r

    def delete(self):
        'Delete this file and return the new, deleted JFSFile'
        url = '%s?dl=true' % self.path
        r = self.jfs.post(url)
        return r

    def rename(self, newpath):
        "Move file to a new name, possibly a whole new path"
        # POST https://www.jottacloud.com/jfs/**USERNAME**/Jotta/Sync/testFolder/testFile.txt?mv=/**USERNAME**/Jotta/Sync/testFolder/renamedTestFile.txt
        url = '%s?mv=/%s%s' % (self.path, self.jfs.username, newpath)
        r = self.jfs.post(url, extra_headers={'Content-Type':'application/octet-stream'})
        return r

    def thumb(self, size=BIGTHUMB):
        'Get a thumbnail as string or None if the file isnt an image'
        if not self.is_image():
            return None

        thumbmap = {self.BIGTHUMB:'WL',
                    self.MEDIUMTHUMB:'WM',
                    self.SMALLTHUMB:'WS'}
        return self.jfs.raw('%s?mode=thumb&ts=%s' % (self.path, thumbmap[size]))

    def is_deleted(self):
        'Return bool based on self.deleted'
        return self.deleted is not None

    @property
    def revisionNumber(self):
        'return int of current revision'
        return int(self.f.currentRevision.number)

    @property
    def created(self):
        'return datetime.datetime'
        return dateutil.parser.parse(str(self.f.currentRevision.created))

    @property
    def modified(self):
        'return datetime.datetime'
        return dateutil.parser.parse(str(self.f.currentRevision.modified))

    @property
    def updated(self):
        'return datetime.datetime'
        return dateutil.parser.parse(str(self.f.currentRevision.updated))

    @property
    def size(self):
        'return int of size in bytes'
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

class JFSMountPoint(JFSFolder):
    'OO interface to a mountpoint, for convenient access. Type less, do more.'
    def __init__(self, mountpointobject, jfs, parentpath): # folderobject from lxml.objectify
        super(JFSMountPoint, self).__init__(mountpointobject, jfs, parentpath)
        self.mp = mountpointobject
        # del(self.folder)

    @property
    def name(self):
        return unicode(self.mp.name)

    @property
    def size(self):
        'Return int of size in bytes'
        return int(self.mp.size)

    @property
    def modified(self):
        'Return datetime.datetime'
        return dateutil.parser.parse(str(self.dev.modified))

class JFSDevice(object):
    'OO interface to a device, for convenient access. Type less, do more.'
    """
    <device time="2014-02-20-T21:02:42Z" host="dn-036.site-000.jotta.no">
  <name xml:space="preserve">laptop</name>
  <type>LAPTOP</type>
  <sid>d831efc4-f885-4d97-bd8d-</sid>
  <size>371951820971</size>
  <modified>2014-02-20-T14:03:52Z</modified>
  <user>hgl</user>
  <mountPoints>
    <mountPoint>
      <name xml:space="preserve">backup</name>
      <size>372544055053</size>
      <modified>2014-02-20-T14:03:52Z</modified>
    </mountPoint>
    <mountPoint>
      <name xml:space="preserve">Desktop</name>
      <size>581758</size>
      <modified>2010-11-12-T20:44:15Z</modified>
    </mountPoint>
    <mountPoint>
      <name xml:space="preserve">Documents</name>
      <size>417689097</size>
      <modified>2010-12-19-T22:40:16Z</modified>
    </mountPoint>
    <mountPoint>
      <name xml:space="preserve">Downloads</name>
      <size>0</size>
      <modified>2010-11-14-T21:00:07Z</modified>
    </mountPoint>
    <mountPoint>
      <name xml:space="preserve">Pictures</name>
      <size>5150529</size>
      <modified>2010-11-29-T11:13:03Z</modified>
    </mountPoint>
    <mountPoint>
      <name xml:space="preserve">Videos</name>
      <size>13679997</size>
      <modified>2010-11-29-T11:13:46Z</modified>
    </mountPoint>
  </mountPoints>
  <metadata first="" max="" total="6" num_mountpoints="6"/>
</device>
"""
    def __init__(self, deviceobject, jfs, parentpath): # deviceobject from lxml.objectify
        self.dev = deviceobject
        self._jfs = jfs
        self.parentPath = parentpath
        self.mountPoints = {unicode(mp.name):mp for mp in self.mountpointobjects()}

    def contents(self, path=None):
        if isinstance(path, lxml.objectify.ObjectifiedElement) and hasattr(path, 'name'):
            # passed an object, use .'name' as path value
            path = '/%s' % path.name
        c = self._jfs.get('%s%s' % (self.path, path or '/'))
        return c

    def mountpointobjects(self):
        return [ JFSMountPoint(obj, self._jfs, self.path) for obj in self.contents().mountPoints.iterchildren() ]

    def files(self, mountPoint):
        """Get an iterator of JFSFile() from the given mountPoint.

        "mountPoint" may be either an actual mountPoint element from JFSDevice.mountPoints{} or its .name. """
        if isinstance(mountPoint, basestring):
            # shortcut: pass a mountpoint name
            mountPoint = self.mountPoints[mountPoint]
        try:
            return [JFSFile(f, self, parentpath='%s/%s' % (self.path, mountPoint.name)) for f in self.contents(mountPoint).files.iterchildren()]
        except AttributeError as err:
            # no files at all
            return [x for x in []]

    def folders(self, mountPoint):
        """Get an iterator of JFSFolder() from the given mountPoint.

        "mountPoint" may be either an actual mountPoint element from JFSDevice.mountPoints{} or its .name. """
        if isinstance(mountPoint, basestring):
            # shortcut: pass a mountpoint name
            mountPoint = self.mountPoints[mountPoint]
        try:
            return [JFSFolder(f, self, parentpath='%s/%s' % (self.path, mountPoint.name)) for f in self.contents(mountPoint).folders.iterchildren()]
        except AttributeError as err:
            # no files at all
            return [x for x in []]

    @property
    def modified(self):
        'Return datetime.datetime'
        return dateutil.parser.parse(str(self.dev.modified))

    @property
    def path(self):
        return os.path.join(self.parentPath, self.name)
        # return '%s/%s' % (self.parentPath, self.name)

    @property
    def name(self):
        return unicode(self.dev.name)

    @property
    def type(self):
        return unicode(self.dev.type)

    @property
    def size(self):
        'Return int of size in bytes'
        return int(self.dev.size)

    @property
    def sid(self):
        return str(self.dev.sid)

class JFSenableSharing(object):
    'wrap enableSharing element in a python class'
    """<enableSharing>
  <files>
    <file name="V1B.docx" uuid="d4490ff3-505c-4ecd-9994-583a6668d3b9">
      <publicURI>33cb006a8ec6493a9dabab48503d022b</publicURI>
      <currentRevision>
        <number>1</number>
        <state>COMPLETED</state>
        <created>2014-10-08-T17:26:12Z</created>
        <modified>2014-10-08-T17:26:12Z</modified>
        <mime>application/msword</mime>
        <mstyle>APPLICATION_MSWORD</mstyle>
        <size>12882</size>
        <md5>5074ad00d3d97f9b938c46c78a97e817</md5>
        <updated>2014-10-08-T15:27:10Z</updated>
      </currentRevision>
    </file>
  </files>
</enableSharing>"""
    def __init__(self, sharing, jfs): # deviceobject from lxml.objectify
        self.sharing = sharing
        self.jfs = jfs

    def sharedFiles(self):
        'iterate over shared files and get their public URI'
        for f in self.sharing.files.iterchildren():
            yield (f.attrib['name'], f.attrib['uuid'],
                'http://www.jottacloud.com/p/%s/%s' % (self.jfs.username, f.publicURI.text))


class JFS(object):
    def __init__(self, username, password, ca_bundle=True):
        from requests.auth import HTTPBasicAuth
        self.apiversion = '2.2' # hard coded per october 2014
        self.session = requests.Session() # create a session for connection pooling, ssl keepalives and cookie jar
        self.username = username
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.verify = ca_bundle
        self.session.headers =  {'User-Agent':'jottalib %s (https://gitorious.org/jottafs/jottalib)' % (__version__, ),
                                 'X-JottaAPIVersion': self.apiversion,
                                }
        self.rootpath = JFS_ROOT + username
        self.fs = self.get(self.rootpath)

    def request(self, url, usecache=True, extra_headers=None):
        'Make a GET request for url, with or without caching'
        if not url.startswith('http'):
            # relative url
            url = self.rootpath + url
        logging.debug("getting url: %s, usecache=%s, extra_headers=%s", url, usecache, extra_headers)
        if extra_headers is None: extra_headers={}
        if usecache:
            r = self.session.get(url, headers=extra_headers)
        else:
            with requests_cache.disabled():
                r = self.session.get(url, headers=extra_headers)

        if r.status_code in ( 500, ):
            raise JFSError(r.reason)
        return r

    def raw(self, url, usecache=True, extra_headers=None):
        'Make a GET request for url and return whatever content we get'
        r = self.request(url, usecache=usecache, extra_headers=extra_headers)
        # uncomment to dump raw xml
        # f = open('/tmp/%s.xml' % time.time(), 'wb')
        # f.write(r.content)
        # f.close()
        return r.content

    def get(self, url, usecache=True):
        'Make a GET request for url and return the response content as a generic lxml object'
        o = lxml.objectify.fromstring(self.raw(url, usecache=usecache))
        if o.tag == 'error':
            JFSError.raiseError(o, url)
        return o

    def getObject(self, url_or_requests_response, usecache=True):
        'Take a url or some xml response from JottaCloud and wrap it up with the corresponding JFS* class'
        if isinstance(url_or_requests_response, requests.models.Response):
            url = url_or_requests_response.url
            o = lxml.objectify.fromstring(url_or_requests_response.content)
        else:
            url = url_or_requests_response
            o = self.get(url, usecache=usecache)

        parent = os.path.dirname(url).replace('up.jottacloud.com', 'www.jotta.no')
        if o.tag == 'error':
            JFSError.raiseError(o, url)
        elif o.tag == 'device': return JFSDevice(o, jfs=self, parentpath=parent)
        elif o.tag == 'folder': return JFSFolder(o, jfs=self, parentpath=parent)
        elif o.tag == 'mountPoint': return JFSMountPoint(o, jfs=self, parentpath=parent)
        elif o.tag == 'file':
            try:
                if o.latestRevision.state == 'INCOMPLETE':
                    return JFSIncompleteFile(o, jfs=self, parentpath=parent)
            except AttributeError:
                return JFSFile(o, jfs=self, parentpath=parent)
        elif o.tag == 'enableSharing': return JFSenableSharing(o, jfs=self)
        elif o.tag == 'user':
            self.fs = o
            return self.fs
        raise JFSError("invalid object: %s <- %s" % (repr(o), url_or_requests_response))

    def stream(self, url, chunkSize=1024):
        'Iterator to get remote content by chunkSize (bytes)'
        r = self.request(url)
        for chunk in r.iter_content(chunkSize):
            yield chunk

    def post(self, url, content='', files=None, params=None, extra_headers={}):
        'HTTP Post files[] or content (unicode string) to url'
        if not url.startswith('http'):
            # relative url
            url = self.rootpath + url
        logging.debug('yanking url from cache: %s', url)
        cache = requests_cache.core.get_cache()
        cache.delete_url(url)
        logging.debug('posting content (len %s) to url %s', content is not None and len(content) or '?', url)
        headers = self.session.headers.copy()
        headers.update(**extra_headers)
        r = self.session.post(url, data=content, params=params, files=files, headers=headers)
        if r.status_code in ( 500, 404, 401, 403, 400 ):
            logging.warning('HTTP POST failed: %s', r.text)
            raise JFSError(r.reason)
        return self.getObject(r) # return a JFS* class

    def up(self, path, fileobject):
        "Upload a fileobject to path, HTTP POST-ing to up.jottacloud.com, using the JottaCloud API"
        """

        *** WHAT DID I DO?: created file
        ***

        POST https://up.jottacloud.com/jfs/**USERNAME**/Jotta/Sync/testFolder/testFile.txt?cphash=d41d8cd98f00b204e9800998ecf8427e HTTP/1.1
        User-Agent: Desktop_Jottacloud 3.0.22.203 Windows_8 6.2.9200 x86_64
        Authorization: Basic ******************
        X-JottaAPIVersion: 2.2
        X-Jfs-DeviceName: **CENSORED**
        JCreated: 2014-10-26T12:33:09Z+00:00
        JModified: 2014-10-26T12:33:09Z+00:00
        JMd5: d41d8cd98f00b204e9800998ecf8427e
        JSize: 0
        jx_csid: dOq1NCRer6uxuR/bFxihasj4QzBU3Tn7S2jVF1CE71YW1fGhxPFYYsw2T0XYjnJBtxKQzhWixmg+u5kp8bJtvMpIFHbhSDmPPSk+PVBf2UdFhXxli4YEII9a97eO4XBfn5QWAV1LJ2Z9l59jmnLkJQgfOyexkuQbxHdSLgQPXu8=
        jx_lisence: M1v3p31oQf2OXvyAn2GvfS2I2oiMXrw+cofuMVHHI/2K+wlxhj22VkON6fN6fJMsGNcMzvcFYfmKPgL0Yf8TCO5A/6ULk6N8LctY3+fPegx+Jgbyc4hh0IXwnOdqa+UZ6Lg1ub4VXr5XnX3P3IxeVDg0VbcJnzv4TbFA+oMXmfM=
        Content-Type: application/octet-stream
        Content-Length: 0
        Connection: Keep-Alive
        Accept-Encoding: gzip
        Accept-Language: nb-NO,en,*
        Host: up.jottacloud.com
        """
        url = path.replace('www.jotta.no', 'up.jottacloud.com')
        content = fileobject.read()
        fileobject.seek(0) # rewind read index for requests.post
        md5hash = hashlib.md5(content).hexdigest() # TODO: read (big) files in chunks to avoid memory errors
        logging.debug('posting content (len %s, hash %s) to url %s', len(content), md5hash, url)
        now = datetime.datetime.now().isoformat()
        headers = {'JMd5':md5hash,
                   'JCreated': now,
                   'JModified': now,
                   'X-Jfs-DeviceName': 'Jotta',
                   'JSize': len(content),
                   'jx_csid': '',
                   'jx_lisence': ''
                   }
        #TODO: enable partial uploading using HTTP Range bytes=start
        params = {'cphash':md5hash,}
        files = {'md5': ('', md5hash),
                 'modified': ('', now),
                 'created': ('', now),
                 'file': (os.path.basename(url), fileobject, 'application/octet-stream', {'Content-Transfer-Encoding':'binary'})}
        return self.post(url, None, files=files, params=params, extra_headers=headers)

    # property overloading
    @property
    def devices(self):
        'return generator of configured devices'
        return self.fs is not None and [JFSDevice(d, self, parentpath=self.rootpath) for d in self.fs.devices.iterchildren()] or [x for x in []]

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
        'Return int of storage capacity in bytes. A value of -1 means "unlimited"'
        return self.fs is not None and int(self.fs.capacity) or 0

    @property
    def usage(self):
        'Return int of storage usage in bytes'
        return self.fs is not None and int(self.fs.usage) or 0


if __name__=='__main__':
    # debug setup
    import httplib as http_client
    logging.basicConfig(level=logging.DEBUG)
    #http_client.HTTPConnection.debuglevel = 1
    #requests_log = logging.getLogger("requests.packages.urllib3")
    #requests_log.setLevel(logging.DEBUG)
    #requests_log.propagate = True
    from lxml.objectify import dump as xdump
    from pprint import pprint
    import netrc
    try:
        n = netrc.netrc()
        username, account, password = n.authenticators('jottacloud') # read .netrc entry for 'machine jottacloud'
    except Exception as e:
        logging.exception(e)
        username = os.environ['JOTTACLOUD_USERNAME']
        password = os.environ['JOTTACLOUD_PASSWORD']

    jfs = JFS(username, password)
    #logging.info(xdump(jfs.fs))
    jottadev = None
    for j in jfs.devices:
        if j.name == 'Jotta':
            jottadev = j
    jottasync = jottadev.mountPoints['Sync']
    try:
        _filename = sys.argv[1]
    except IndexError:
        _filename = '/tmp/test.pdf'
    r = jottasync.up(_filename)
