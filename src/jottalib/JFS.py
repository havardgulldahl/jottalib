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
import posixpath, logging, datetime, hashlib
from collections import namedtuple
import six
from six.moves import cStringIO as StringIO

# importing external dependencies (pip these, please!)
import requests
from requests.utils import quote
import netrc
import requests_toolbelt
import certifi

import lxml, lxml.objectify
import dateutil, dateutil.parser # pip install python-dateutil

log = logging.getLogger(__name__)

#monkeypatch urllib3 param function to bypass bug in jottacloud servers
from requests.packages import urllib3
urllib3.fields.format_header_param_orig = urllib3.fields.format_header_param
def mp(name, value):
    return urllib3.fields.format_header_param_orig(name, value).replace('filename*=', 'filename=')
urllib3.fields.format_header_param = mp

# some setup
JFS_ROOT='https://www.jottacloud.com/jfs/'

# helper functions
try:
    unicode("we are python2")
except NameError:
    def unicode(s): return str(s) # TODO: use six
##
# A note regarding the use of unicode() to convert string values from XML object nodes (lxml.objectify)
#
# you are always safe to convert objectify.StringElements to native Python unicode objects using unicode()
# - https://mailman-mail5.webfaction.com/pipermail/lxml/2011-February/005885.html
#


def get_auth_info():
    """ Get authentication details to jottacloud.

    Will first check environment variables, then the .netrc file.
    """
    env_username = os.environ.get('JOTTACLOUD_USERNAME')
    env_password = os.environ.get('JOTTACLOUD_PASSWORD')
    netrc_auth = None
    try:
        netrc_file = netrc.netrc()
        netrc_auth = netrc_file.authenticators('jottacloud.com')
    except IOError:
        # .netrc file doesn't exist
        pass
    netrc_username = None
    netrc_password = None
    if netrc_auth:
        netrc_username, _, netrc_password = netrc_auth
    username = env_username or netrc_username
    password = env_password or netrc_password
    if not (username and password):
        raise JFSError('Could not find username and password in either env or ~/.netrc, '
            'you need to add one of these to use these tools')
    return (username, password)

def calculate_md5(fileobject, size=2**16):
    """Utility function to calculate md5 hashes while being light on memory usage.

    By reading the fileobject piece by piece, we are able to process content that
    is larger than available memory"""
    fileobject.seek(0)
    md5 = hashlib.md5()
    for data in iter(lambda: fileobject.read(size), b''):
        if isinstance(data, unicode):
            data = data.encode('utf-8') # md5 needs a byte string
        md5.update(data)
    fileobject.seek(0) # rewind read head
    return md5.hexdigest()

# error classes

class JFSError(Exception):
    @staticmethod
    def raiseError(e, path): # parse object from lxml.objectify and
        if(e.code) == 404:
            raise JFSNotFoundError('%s does not exist (%s)' % (path, e.message))
        elif(e.code) == 401:
            raise JFSCredentialsError("Your credentials don't match for %s (%s) (probably incorrect password!)" % (path, e.message))
        elif(e.code) == 403:
            raise JFSAuthenticationError("You don't have access to %s (%s)" % (path, e.message))
        elif(e.code) == 416:
            raise JFSRangeError("Requested Range Not Satisfiable (%s)" % e.message)
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

class JFSRangeError(JFSError): # HTTP 416
    pass

class JFSServerError(JFSError): # HTTP 500
    pass

# classes mapping JFS structures


class JFSFileDirList(object):
    '''Wrapping <filedirlist>, a simple tree of folders and their files

       Get a <filedirlist> for any jottafolder by appending ?mode=list to your query

       Then you will get this object, with a .tree property, which is a list of all
       files and folders.

       Files will be a namedtuple() with five properties:
         .name - file name
         .state - file state (str): one of JFS.ProtoFile.STATE_*, e.g 'COMPLETED' or 'INCOMPLETE'
         .size - file size (int or None): full size , partially uploaded size or no size, depentant on file state
         .md5 - jottacloud file hash (str or None): corrupt files have no md5 hash
         .uuid - jottacloud assigned uuid

    <filedirlist time="2015-05-28-T18:57:06Z" host="dn-093.site-000.jotta.no">
        <folders>
          <folder name="Sync">
            <path xml:space="preserve">/havardgulldahl/Jotta</path>
            <abspath xml:space="preserve">/havardgulldahl/Jotta</abspath>
            <files>
                <file>...'''


    def __init__(self, filedirlistobject, jfs, parentpath): # filedirlistobject from lxml.objectify
        self.filedirlist = filedirlistobject
        self.parentPath = parentpath
        self.jfs = jfs

        treefile = namedtuple('TreeFile', 'name size md5 uuid state')

        self.tree = {}
        for folder in self.filedirlist.folders.iterchildren():
            foldername = unicode(folder.attrib.get('name'))
            path = unicode(folder.path)
            t = []
            if hasattr(folder, 'files'):
                for file_ in folder.files.iterchildren():
                    if hasattr(file_, 'currentRevision'): # a normal file
                        t.append(treefile(unicode(file_.attrib['name']),
                                          int(file_.currentRevision.size),
                                          unicode(file_.currentRevision.md5),
                                          unicode(file_.attrib['uuid']),
                                          unicode(file_.currentRevision.state)
                                          )
                                 )
                    else:
                        # This is an incomplete or, possibly, corrupt file
                        #
                        # Incomplete files have no `size` in a filedirlist, you
                        # need to fetch the JFSFile explicitly to see that property
                        try:
                            # incomplete files carry a md5 hash,
                            _md5 = unicode(file_.latestRevision.md5)
                        except AttributeError:
                            # while other may not
                            # see discussion in #88
                            _md5 = None
                        t.append(treefile(unicode(file_.attrib['name']),
                                          None, # return size as None
                                          _md5,
                                          unicode(file_.attrib['uuid']),
                                          unicode(file_.latestRevision.state)
                                          )
                                 )
            self.tree[posixpath.join(path, foldername)] = t



class JFSFolder(object):
    'OO interface to a folder, for convenient access. Type less, do more.'
    def __init__(self, folderobject, jfs, parentpath): # folderobject from lxml.objectify
        self.folder = folderobject
        self.parentPath = parentpath
        self.jfs = jfs
        self.synced = False

    @property
    def name(self):
        if self.folder.attrib.has_key('name'):
            return unicode(self.folder.attrib['name'])
        return unicode(self.folder.name)

    @property
    def path(self):
        log.debug('path: %r + %r', self.parentPath, self.name)
        return '%s/%s' % (self.parentPath, self.name)

    @property
    def deleted(self):
        'Return datetime.datetime or None if the file isnt deleted'
        _d = self.folder.attrib.get('deleted', None)
        if _d is None: return None
        return dateutil.parser.parse(str(_d))

    def sync(self):
        'Update state of folder from Jottacloud server'
        log.info("syncing %r" % self.path)
        self.folder = self.jfs.get(self.path)
        self.synced = True

    def is_deleted(self):
        'Return bool based on self.deleted'
        return self.deleted is not None

    def files(self):
        if not self.synced:
            self.sync()
        try:
            #return [JFSFile(f, self.jfs, self.path) for f in self.folder.files.iterchildren()]
            for _f in self.folder.files.iterchildren():
                if hasattr(_f, 'currentRevision'): # a normal file
                    yield JFSFile(_f, self.jfs, self.path)
                else:
                    yield JFSIncompleteFile(_f, self.jfs, self.path)

        except AttributeError:
            while False:
                yield None
            #return [x for x in []]

    def folders(self):
        if not self.synced:
            self.sync()
        try:
            return [JFSFolder(f, self.jfs, self.path) for f in self.folder.folders.iterchildren()]
        except AttributeError:
            return [x for x in []]

    def mkdir(self, foldername):
        'Create a new subfolder and return the new JFSFolder'
        url = '%s?mkDir=true' % posixpath.join(self.path, foldername)
        r = self.jfs.post(url)
        self.sync()
        return r

    def restore(self):
        'Restore the folder'
        #
        #
        # As of 2016-06-15, Jottacloud.com has changed their restore api
        # To restore, this is what's done
        #
        # HTTP POST to https://www.jottacloud.com/web/restore/trash/list
        # Data:
        #     hash:undefined
        #     files:@0025d37be5329a18eece18dd93f793509e8_dGVzdF9kZWxldGUudHh0
        #
        # where `files` is a comma separated list, and each item is constructed thus:
        #  @<uuid of path>_<base64 encoded file name>
        #
        if not self.deleted:
            raise JFSError('Tried to restore a not deleted folder')
        raise NotImplementedError
        url = 'https://www.jottacloud.com/rest/webrest/%s/action/restore' % self.jfs.username
        data = {'paths[]': self.path.replace(JFS_ROOT, ''),
                'web': 'true',
                'ts': int(time.time()),
                'authToken': 0}
        r = self.jfs.post(url, content=data)
        return r

    def delete(self):
        'Delete this folder and return a deleted JFSFolder'
        url = '%s?dlDir=true' % self.path
        r = self.jfs.post(url)
        self.sync()
        return r

    def hard_delete(self):
        'Deletes without possibility to restore'
        url = 'https://www.jottacloud.com/rest/webrest/%s/action/delete' % self.jfs.username
        data = {'paths[]': self.path.replace(JFS_ROOT, ''),
                'web': 'true',
                'ts': int(time.time()),
                'authToken': 0}
        r = self.jfs.post(url, content=data)
        return r


    def rename(self, newpath):
        "Move folder to a new name, possibly a whole new path"
        # POST https://www.jottacloud.com/jfs/**USERNAME**/Jotta/Sync/Ny%20mappe?mvDir=/**USERNAME**/Jotta/Sync/testFolder
        url = '%s?mvDir=/%s%s' % (self.path, self.jfs.username, newpath)
        r = self.jfs.post(url, extra_headers={'Content-Type':'application/octet-stream'})
        return r

    def up(self, fileobj_or_path, filename=None, upload_callback=None):
        'Upload a file to current folder and return the new JFSFile'
        close_on_done = False

        if isinstance(fileobj_or_path, six.string_types):
            filename = filename or os.path.basename(fileobj_or_path)
            fileobj_or_path = open(fileobj_or_path, 'rb')
            close_on_done = True
        elif hasattr(fileobj_or_path, 'read'):  # file like
            pass
        else:
            # TODO: handle generators here?
            raise JFSError("Need filename or file-like object")

        if filename is None:
            if hasattr(fileobj_or_path, 'name'):
                filename = os.path.basename(fileobj_or_path.name)
            else:
                raise JFSError("Unable to guess filename")

        log.debug('.up %s ->  %s %s', repr(fileobj_or_path), repr(self.path), repr(filename))
        r = self.jfs.up(posixpath.join(self.path, filename), fileobj_or_path,
            upload_callback=upload_callback)
        if close_on_done:
            fileobj_or_path.close()
        self.sync()
        return r

    def filedirlist(self):
        'Get a JFSFileDirList, recursive tree of JFSFile and JFSFolder'
        url = '%s?mode=list' % self.path
        return self.jfs.getObject(url)

class ProtoFile(object):
    'Prototype for different incarnations fo file, e.g. JFSIncompleteFile and JFSFile'

    # constants for known file states
    STATE_COMPLETED = 'COMPLETED' # -> JFSFile
    STATE_ADDED = 'ADDED'
    STATE_INCOMPLETE = 'INCOMPLETE' # -> JFSIncompleteFile
    STATE_PROCESSING = 'PROCESSING'
    STATE_CORRUPT = 'CORRUPT' # -> JFSCorruptFile
    @staticmethod
    def factory(fileobject, jfs, parentpath): # fileobject from lxml.objectify
        'Class method to get the correct file class instatiated'
        if hasattr(fileobject, 'currentRevision'): # a normal file
            return JFSFile(fileobject, jfs, parentpath)
        elif str(fileobject.latestRevision.state) == ProtoFile.STATE_INCOMPLETE:
            return JFSIncompleteFile(fileobject, jfs, parentpath)
        elif str(fileobject.latestRevision.state) == ProtoFile.STATE_CORRUPT:
            return JFSCorruptFile(fileobject, jfs, parentpath)
        else:
            raise NotImplementedError('No JFS*File support for state %r. Please file a bug!' % fileobject.latestRevision.state)

    def __init__(self, fileobject, jfs, parentpath): # fileobject from lxml.objectify
        self.f = fileobject
        self.jfs = jfs
        self.parentPath = parentpath

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

    def is_deleted(self):
        'Return bool based on self.deleted'
        return self.deleted is not None

    @property
    def path(self):
        return posixpath.join(self.parentPath, self.name)


class JFSCorruptFile(ProtoFile):
    'OO interface to a corrupt file.'
    """
 18     <revision>
 19       <number>3</number>
 20       <state>CORRUPT</state>
 21       <created>2016-06-14-T19:09:47Z</created>
 22       <modified>2016-06-14-T19:09:47Z</modified>
 23       <mime>text/plain</mime>
 24       <mstyle>text/plain</mstyle>
 25       <md5>2ed82c2b9a78f3fce85b19592fc94581</md5>
 26       <updated>2016-06-14-T19:09:48Z</updated>
 27     </revision>"""

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

class JFSIncompleteFile(JFSCorruptFile):
    'OO interface to an incomplete file. Like JFSCorruptFile, but adds a .size property and a .resume() method.'
    """<file name="iii.m4v" uuid="e8f268ac-d081-4d4f-bfb1-77149b2bd51d" time="2015-05-29-T18:11:56Z" host="dn-091.site-000.jotta.no">
  <path xml:space="preserve">/havardgulldahl/Jotta/Sync</path>
  <abspath xml:space="preserve">/havardgulldahl/Jotta/Sync</abspath>
  <latestRevision>
    <number>1</number>
    <state>INCOMPLETE</state>
    <created>2014-05-22-T22:13:52Z</created>
    <modified>2014-05-19-T13:37:14Z</modified>
    <mime>video/mp4</mime>
    <mstyle>VIDEO_MP4</mstyle>
    <size>100483008</size> <!-- THIS IS THE SIZE OF WHAT'S BEEN TRANSFERED THIS FAR. havardgulldahl -->
    <md5>4d7cdab5256b72d17075ec388e467e99</md5>
    <updated>2015-05-29-T18:07:56Z</updated>
  </latestRevision>
</file>
</file>"""

    def resume(self, data):
        'Resume uploading an incomplete file, after a previous upload was interrupted. Returns new file object'
        if not hasattr(data, 'read'):
            data = StringIO(data)
        #check if what we're asked to upload is actually the right file
        md5 = calculate_md5(data)
        if md5 != self.md5:
            raise JFSError('''MD5 hashes don't match! Are you trying to resume with the wrong file?''')
        log.debug('Resuming %s from offset %s', self.path, self.size)
        return self.jfs.up(self.path, data, resume_offset=self.size)

    @property
    def size(self):
        """Bytes uploaded of the file so far.

        Note that we only have the file size if the file was requested directly,
        not if it's part of a folder listing.
        """
        if hasattr(self.f.latestRevision, 'size'):
            return int(self.f.latestRevision.size)
        return None

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
    # Constants for thumb nail sizes
    BIGTHUMB='WL'
    MEDIUMTHUMB='WM'
    SMALLTHUMB='WS'
    XLTHUMB='WXL'

    def __init__(self, fileobject, jfs, parentpath): # fileobject from lxml.objectify
        self.f = fileobject
        self.jfs = jfs
        self.parentPath = parentpath

    def stream(self, chunk_size=64*1024):
        'Returns a generator to iterate over the file contents'
        return self.jfs.stream(url='%s?mode=bin' % self.path, chunk_size=chunk_size)

    def read(self):
        'Get the file contents as string'
        return self.jfs.raw('%s?mode=bin' % self.path)
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
                            # note that we deduct 1 from end because
                            # in http Range requests, the end value is included in the slice,
                            # whereas in python, it is not
                            extra_headers={'Range':'bytes=%s-%s' % (start, end-1)})

    def write(self, data):
        'Put, possibly replace, file contents with (new) data'
        if not hasattr(data, 'read'):
            data = StringIO(data)
        self.jfs.up(self.path, data)

    def share(self):
        'Enable public access at secret, share only uri, and return that uri'
        # This is what jottacloud.com does
        # HTTP GET to
        #
        # https://www.jottacloud.com/web/share/{sync,backup,archive}/list/[folder uuid]/@[base64-encodded basename]?t=[timestamp]
        #
        # e.g.
        # https://www.jottacloud.com/web/share/backup/list/002c7707c2b27604dc4670660961a33a648/@YmzDpWLDpnIudXRmOC50eHQ=?t=1465934084756
        # https://www.jottacloud.com/web/share/backup/list/002c7707c2b27604dc4670660961a33a648/@YmzDpWLDpnIudXRmOC50eHQ=?t=1465934084756
        #
        #
        raise NotImplementedError('Jottacloud has changed the sharing API. Please use jottacloud.com in a browser, for now.')
        url = 'https://www.jottacloud.com/rest/webrest/%s/action/enableSharing' % self.jfs.username
        data = {'paths[]':self.path.replace(JFS_ROOT, ''),
                'web':'true',
                'ts':int(time.time()),
                'authToken':0}
        r = self.jfs.post(url, content=data)
        return r

    def restore(self):
        'Restore the file'
        #
        #
        # As of 2016-06-15, Jottacloud.com has changed their restore api
        # To restore, this is what's done
        #
        # HTTP POST to https://www.jottacloud.com/web/restore/trash/list
        # Data:
        #     hash:undefined
        #     files:@0025d37be5329a18eece18dd93f793509e8_dGVzdF9kZWxldGUudHh0
        #
        # where `files` is a comma separated list, and each item is constructed thus:
        #  @<uuid of path>_<base64 encoded file name>
        #
        if not self.deleted:
            raise JFSError('Tried to restore a not deleted file')
        raise NotImplementedError('Jottacloud has changed the restore API. Please use jottacloud.com in a browser, for now.') #  TODO: figure out how to solve this
        url = 'https://www.jottacloud.com/rest/webrest/%s/action/restore' % self.jfs.username
        data = {'paths[]': self.path.replace(JFS_ROOT, ''),
                'web': 'true',
                'ts': int(time.time()),
                'authToken': 0}
        r = self.jfs.post(url, content=data)
        return r

    def hard_delete(self):
        'Deletes without possibility to restore'
        url = 'https://www.jottacloud.com/rest/webrest/%s/action/delete' % self.jfs.username
        data = {'paths[]': self.path.replace(JFS_ROOT, ''),
                'web': 'true',
                'ts': int(time.time()),
                'authToken': 0}
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
        '''Get a thumbnail as string or None if the file isnt an image

        size would be one of JFSFile.BIGTHUMB, .MEDIUMTHUMB, .SMALLTHUMB or .XLTHUMB'''
        if not self.is_image():
            return None
        if not size in (self.BIGTHUMB, self.MEDIUMTHUMB, self.SMALLTHUMB, self.XLTHUMB):
            raise JFSError('Invalid thumbnail size: %s for image %s' % (size, self.path))

        return self.jfs.raw('%s?mode=thumb&ts=%s' % (self.path, size))

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
        self.folder = mountpointobject # name it 'folder' because of inheritance

    def delete(self):
        "override inherited method that makes no sense here"
        raise JFSError('Cant delete a mountpoint')

    def rename(self, newpath):
        "override inherited method that makes no sense here"
        raise JFSError('Cant rename a mountpoint')

    @property
    def name(self):
        return unicode(self.folder.name)

    @property
    def size(self):
        'Return int of size in bytes'
        return int(self.folder.size)

    @property
    def modified(self):
        'Return datetime.datetime'
        return dateutil.parser.parse(str(self.folder.modified))

class JFSDevice(object):
    '''OO interface to a device, for convenient access. Type less, do more.


    Note that sometimes we cheat a little and instantiate this object with only the elements
    available from <user>, in which case some elements aren't there.'''
    """ raw xml example:
    <device time="2014-02-20-T21:02:42Z" host="dn-036.site-000.jotta.no">
  <name xml:space="preserve">laptop</name>
  <type>LAPTOP</type>
  <sid>d831efc4-f885-4d97-bd8d-</sid>
  <size>371951820971</size>
  <modified>2014-02-20-T14:03:52Z</modified>
  <!-- the following elements are only available if we get the metadata from
       the http path explicitly.
       you won't find it here under the <user/> element -->
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
        """Get _all_ metadata for this device.
        Call this method if you have the lite/abbreviated device info from e.g. <user/>. """
        if isinstance(path, object) and hasattr(path, 'name'):
            log.debug("passed an object, use .'name' as path value")
            # passed an object, use .'name' as path value
            path = '/%s' % path.name
        c = self._jfs.get('%s%s' % (self.path, path or '/'))
        return c

    def mountpointobjects(self):
        try:
            return [ JFSMountPoint(obj, self._jfs, self.path) for obj in self.contents().mountPoints.iterchildren() ]
        except AttributeError:
            # there are no mountpoints. this may happen on newly created devices. see github bug#26
            return []

    def files(self, mountPoint):
        """Get an iterator of JFSFile() from the given mountPoint.

        "mountPoint" may be either an actual mountPoint element from JFSDevice.mountPoints{} or its .name. """
        if isinstance(mountPoint, six.string_types):
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
        if isinstance(mountPoint, six.string_types):
            # shortcut: pass a mountpoint name
            mountPoint = self.mountPoints[mountPoint]
        try:
            return [JFSFolder(f, self, parentpath='%s/%s' % (self.path, mountPoint.name)) for f in self.contents(mountPoint).folders.iterchildren()]
        except AttributeError as err:
            # no files at all
            return [x for x in []]

    def new_mountpoint(self, name):
        """Create a new mountpoint"""
        url = posixpath.join(self.path, name)
        r = self._jfs.post(url, extra_headers={'content-type': 'application/x-www-form-urlencoded'})
        return r

    @property
    def modified(self):
        'Return datetime.datetime'
        return dateutil.parser.parse(str(self.dev.modified))

    @property
    def path(self):
        return posixpath.join(self.parentPath, self.name)

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
        return unicode(self.dev.sid)

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
                'https://www.jottacloud.com/p/%s/%s' % (self.jfs.username, f.publicURI.text))

class JFSsearchresult(object):
    'wrap searchresult element in a python class'
    """<searchresult  time="2016-06-14-T22:53:43Z" host="dn-098">
  <files>
    <file name="testfile_up_and_readpartial.txt" uuid="f2d204a3-c0fd-4138-86c7-76b12f03a5a6">
    <path xml:space="preserve">/**/Jotta/Archive</path>
    <abspath xml:space="preserve">/**/Jotta/Archive</abspath>
    <currentRevision>
    <number>461</number>
    <state>COMPLETED</state>
    <created>2016-06-14-T22:53:26Z</created>
    <modified>2016-06-14-T22:53:26Z</modified>
    <mime>text/plain</mime>
    <mstyle>text/plain</mstyle>
    <size>347</size>
    <md5>0c963adda33466d565d6f3395490eaee</md5>
    <updated>2016-06-14-T22:53:26Z</updated>
    </currentRevision>
    </file>
  </files>
</enableSharing>"""
    def __init__(self, searchresult, jfs): # deviceobject from lxml.objectify
        self.searchresult = searchresult
        self.jfs = jfs

    @property
    def size(self):
        'Return datetime of search time stamp'
        return dateutil.parser.parse(str(self.searchresult.attrib['time']))

    def files(self):
        'iterate over found files'
        for _f in self.searchresult.files.iterchildren():
            yield ProtoFile.factory(_f, jfs=self.jfs, parentpath=unicode(_f.abspath))



class JFS(object):
    def __init__(self, auth=None):
        from requests.auth import HTTPBasicAuth
        self.apiversion = '2.2' # hard coded per october 2014
        self.session = requests.Session() # create a session for connection pooling, ssl keepalives and cookie jar
        self.session.stream = True
        if not auth:
            auth = get_auth_info()
        self.username, password = auth
        self.session.auth = HTTPBasicAuth(self.username, password)
        self.session.verify = certifi.where()
        self.session.headers =  {'User-Agent':'jottalib %s (https://github.com/havardgulldahl/jottalib)' % (__version__, ),
                                 'X-JottaAPIVersion': self.apiversion,
                                }
        self.rootpath = JFS_ROOT + self.username
        self.fs = self.get(self.rootpath)

    def close(self):
        self.session.close()

    def escapeUrl(self, url):
        if isinstance(url, unicode):
            url = url.encode('utf-8') # urls have to be bytestrings
        separators = [
            '?dl=true',
            '?mkDir=true',
            '?dlDir=true',
            '?mvDir=',
            '?mv=',
            '?mode=list',
            '?mode=bin',
            '?mode=thumb&ts='
        ]
        # TODO: replace this buggy thing with proper param support, that requests will encode for us
        # for free
        separator = separators[0]
        for sep in separators:
            if sep in url:
                separator = sep
                break

        urlparts = url.rsplit(separator, 1)
        if(len(urlparts) == 2):
            url = quote(urlparts[0], safe=self.rootpath) + separator + urlparts[1]
        else:
            url = quote(urlparts[0], safe=self.rootpath)
        return url

    def request(self, url, extra_headers=None, params=None):
        'Make a GET request for url, with or without caching'
        if not url.startswith('http'):
            # relative url
            url = self.rootpath + url
        log.debug("getting url: %r, extra_headers=%r, params=%r", url, extra_headers, params)
        if extra_headers is None: extra_headers={}
        r = self.session.get(url, headers=extra_headers, params=params)

        if r.status_code in ( 500, ):
            raise JFSError(r.reason)
        return r

    def raw(self, url, extra_headers=None, params=None):
        'Make a GET request for url and return whatever content we get'
        r = self.request(url, extra_headers=extra_headers, params=params)
        # uncomment to dump raw xml
#         with open('/tmp/%s.xml' % time.time(), 'wb') as f:
#             f.write(r.content)

        if not r.ok:
            o = lxml.objectify.fromstring(r.content)
            JFSError.raiseError(o, url)
        return r.content

    def get(self, url, params=None):
        'Make a GET request for url and return the response content as a generic lxml object'
        url = self.escapeUrl(url)
        o = lxml.objectify.fromstring(self.raw(url, params=params))
        if o.tag == 'error':
            JFSError.raiseError(o, url)
        return o

    def getObject(self, url_or_requests_response):
        'Take a url or some xml response from JottaCloud and wrap it up with the corresponding JFS* class'
        if isinstance(url_or_requests_response, requests.models.Response):
            url = url_or_requests_response.url
            o = lxml.objectify.fromstring(url_or_requests_response.content)
        else:
            url = url_or_requests_response
            o = self.get(url)

        parent = os.path.dirname(url).replace('up.jottacloud.com', 'www.jottacloud.com')
        if o.tag == 'error':
            JFSError.raiseError(o, url)
        elif o.tag == 'device': return JFSDevice(o, jfs=self, parentpath=parent)
        elif o.tag == 'folder': return JFSFolder(o, jfs=self, parentpath=parent)
        elif o.tag == 'mountPoint': return JFSMountPoint(o, jfs=self, parentpath=parent)
        elif o.tag == 'restoredFiles': return JFSFile(o, jfs=self, parentpath=parent)
        elif o.tag == 'deleteFiles': return JFSFile(o, jfs=self, parentpath=parent)
        elif o.tag == 'file':
            return ProtoFile.factory(o, jfs=self, parentpath=parent)
#             try:
#                 if o.latestRevision.state == 'INCOMPLETE':
#                     return JFSIncompleteFile(o, jfs=self, parentpath=parent)
#                 elif o.latestRevision.state == 'CORRUPT':
#                     return JFSCorruptFile(o, jfs=self, parentpath=parent)
#             except AttributeError:
#                 return JFSFile(o, jfs=self, parentpath=parent)
        elif o.tag == 'enableSharing': return JFSenableSharing(o, jfs=self)
        elif o.tag == 'user':
            self.fs = o
            return self.fs
        elif o.tag == 'filedirlist': return JFSFileDirList(o, jfs=self, parentpath=parent)
        elif o.tag == 'searchresult': return JFSsearchresult(o, jfs=self)
        raise JFSError("invalid object: %s <- %s" % (repr(o), url_or_requests_response))

    def getLatest(self, files=10, sort=None):
        'Yield a list of the n latest files (the server minimum default is 10), optionally sorted by `sort`.'
        url = '/Jotta/Latest'
        params = {'sort': 'updated', 'max':files, 'web':'true'}
        result = self.getObject(self.request(url, params=params))
        for _f in result.files():
            yield _f


    def stream(self, url, chunk_size=64*1024):
        'Iterator to get remote content by chunk_size (bytes)'
        r = self.request(url)
        for chunk in r.iter_content(chunk_size):
            yield chunk

    def post(self, url, content='', files=None, params=None, extra_headers={}, upload_callback=None):
        'HTTP Post files[] or content (unicode string) to url'
        if not url.startswith('http'):
            # relative url
            url = self.rootpath + url

        log.debug('posting content (len %s) to url %s', len(content) if content is not None else '?', url)
        headers = self.session.headers.copy()
        headers.update(**extra_headers)

        if not files is None:
            m = requests_toolbelt.MultipartEncoder(fields=files)
            if upload_callback is not None:
                m_len = m.len # compute value for callback closure
                def callback(monitor):
                    upload_callback(monitor, m_len)

                m = requests_toolbelt.MultipartEncoderMonitor(m, callback)
            headers['content-type'] = m.content_type
        else:
            m = content
        url = self.escapeUrl(url)
        r = self.session.post(url, data=m, params=params, headers=headers)
        if not r.ok:
            log.warning('HTTP POST failed: %s', r.text)
            raise JFSError(r.reason)
        return self.getObject(r) # return a JFS* class

    def up(self, path, fileobject, upload_callback=None, resume_offset=None):
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
        url = path.replace('www.jottacloud.com', 'up.jottacloud.com')
        # Calculate file length
        fileobject.seek(0,2)
        contentlen = fileobject.tell()

        # Rewind read head to correct offset
        # If we're resuming a borked upload, continue from that offset
        fileobject.seek(resume_offset if resume_offset is not None else 0)

        # Calculate file md5 hash
        md5hash = calculate_md5(fileobject)

        log.debug('posting content (len %s, hash %s) to url %s', contentlen, md5hash, url)
        try:
            mtime = os.path.getmtime(fileobject.name)
            timestamp = datetime.datetime.fromtimestamp(mtime).isoformat()
        except Exception as e:
            log.exception('Problems getting mtime from fileobjet: %r', e)
            timestamp = datetime.datetime.now().isoformat()
        params = {'cphash': md5hash}
        m = requests_toolbelt.MultipartEncoder({
             'md5': ('', md5hash),
             'modified': ('', timestamp),
             'created': ('', timestamp),
             'file': (os.path.basename(url), fileobject, 'application/octet-stream'),
        })
        headers = {'JMd5':md5hash,
                   'JCreated': timestamp,
                   'JModified': timestamp,
                   'X-Jfs-DeviceName': 'Jotta',
                   'JSize': contentlen,
                   'jx_csid': '',
                   'jx_lisence': '',
                   'content-type': m.content_type,
                   }
        fileobject.seek(0) # rewind read index for requests.post
        files = {'md5': ('', md5hash),
                 'modified': ('', timestamp),
                 'created': ('', timestamp),
                 'file': (os.path.basename(url), fileobject, 'application/octet-stream')}
        return self.post(url, None, files=files, params=params, extra_headers=headers, upload_callback=upload_callback)

    def new_device(self, name, type):
        """Create a new (backup) device on jottacloud. Types can be one of
        ['workstation', 'imac', 'laptop', 'macbook', 'ipad', 'android', 'iphone', 'windows_phone']
        """
        # at least android client also includes a "cid" with is derived from the unique device id
        # and encrypted with a public key in the apk.  The field appears to be optional
        url = posixpath.join(self.rootpath, name)
        r = self.post(url, {'type': type})
        return r

    # property overloading
    @property
    def devices(self):
        'return generator of configured devices'
        return self.fs is not None and [JFSDevice(d, self, parentpath=self.rootpath) for d in self.fs.devices.iterchildren()] or [x for x in []]

    @property
    def locked(self):
        'return bool'
        return bool(self.fs.locked) if self.fs is not None else None

    @property
    def read_locked(self):
        'return bool'
        return bool(self.fs['read-locked']) if self.fs is not None else None

    @property
    def write_locked(self):
        'return bool'
        return bool(self.fs['write-locked']) if self.fs is not None else None

    @property
    def capacity(self):
        'Return int of storage capacity in bytes. A value of -1 means "unlimited"'
        return int(self.fs.capacity) if self.fs is not None else 0

    @property
    def usage(self):
        'Return int of storage usage in bytes'
        return int(self.fs.usage) if self.fs is not None else 0

