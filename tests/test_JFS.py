# -*- encoding: utf-8 -*-
'Tests for JFS.py'
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
# along with jottafs.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2015 Håvard Gulldahl <havard@gulldahl.no>

# metadata
__author__ = 'havard@gulldahl.no'

# import standardlib
import os, StringIO, logging

# import py.test
import pytest # pip install pytest

# import jotta
from jottalib import JFS, __version__


# we need an active login to test
import netrc
try:
    n = netrc.netrc()
    username, account, password = n.authenticators('jottacloud') # read .netrc entry for 'machine jottacloud'
except Exception as e:
    logging.exception(e)
    username = os.environ['JOTTACLOUD_USERNAME']
    password = os.environ['JOTTACLOUD_PASSWORD']

jfs = JFS.JFS(username, password)


TESTFILEDATA="""
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla est dolor, convallis fermentum sapien in, fringilla congue ligula. Fusce at justo ac felis vulputate laoreet vel at metus. Aenean justo lacus, porttitor dignissim imperdiet a, elementum cursus ligula. Vivamus eu est viverra, pretium arcu eget, imperdiet eros. Curabitur in bibendum."""


class TestJFS:
    def test_login(self):
        assert isinstance(jfs, JFS.JFS)


    def test_root(self):
        import lxml.objectify
        assert isinstance(jfs.fs, lxml.objectify.ObjectifiedElement)
        assert jfs.fs.tag == 'user'

    def test_properties(self):
        assert isinstance(jfs.capacity, int)
        assert isinstance(jfs.usage, int)
        assert isinstance(jfs.locked, bool)
        assert isinstance(jfs.read_locked, bool)
        assert isinstance(jfs.write_locked, bool)

    def test_devices(self):
        assert all(isinstance(item, JFS.JFSDevice) for item in jfs.devices)

    def test_up_and_delete(self):
        p = "/Jotta/Archive/testfile_up_and_delete.txt"
        t = jfs.up(p, StringIO.StringIO(TESTFILEDATA))
        assert isinstance(t, JFS.JFSFile)
        d = t.delete()
        assert isinstance(d, JFS.JFSFile)
        assert d.is_deleted()

    def test_up_and_read(self):
        p = "/Jotta/Archive/testfile_up_and_read.txt"
        t = jfs.up(p, StringIO.StringIO(TESTFILEDATA))
        f = jfs.getObject(p)
        assert isinstance(f, JFS.JFSFile)
        assert f.read() == TESTFILEDATA
        f.delete()

    def test_up_and_readpartial(self):
        import random
        p = "/Jotta/Archive/testfile_up_and_readpartial.txt"
        t = jfs.up(p, StringIO.StringIO(TESTFILEDATA))
        f = jfs.getObject(p)
        # pick a number less than length of text
        start = random.randint(0, len(TESTFILEDATA))
        # pick a number between start and length of text
        end = random.randint(0, len(TESTFILEDATA)-start) + start
        assert f.readpartial(start, end) == TESTFILEDATA[start:end]
        f.delete()

    def test_stream(self):
        p = "/Jotta/Archive/testfile_up_and_stream.txt"
        t = jfs.up(p, StringIO.StringIO(TESTFILEDATA))
        s = "".join( [ chunk for chunk in t.stream() ] )
        assert s == TESTFILEDATA
        t.delete()

    @pytest.mark.xfail
    def test_resume(self):
        raise NotImplementedError

    @pytest.mark.xfail
    def test_post(self):
        raise NotImplementedError
        #TODO: test unicode string upload
        #TODO: test file list upload
        #TODO: test upload_callback

    def test_getObject(self):

        assert isinstance(jfs.getObject('/Jotta'), JFS.JFSDevice)
        assert isinstance(jfs.getObject('/Jotta/Archive'), JFS.JFSMountPoint)
        assert isinstance(jfs.getObject('/Jotta/Archive/test'), JFS.JFSFolder)
        #TODO: test with a python-requests object

    @pytest.mark.xfail
    def test_urlencoded_filename(self):
        # make sure filenames that contain percent-encoded characters are
        # correctly parsed and the percent encoding is preserved
        # https://github.com/havardgulldahl/jottalib/issues/25
        import tempfile, posixpath, urllib, requests
        f = '%2FVolumes%2FMedia%2Ftest.txt'
        p = posixpath.join('/Jotta/Archive', f)
        _f = tempfile.NamedTemporaryFile(prefix=f)
        _f.write('123test')
        jfs_f = jfs.up(p, _f)
        clean_room_path = '%s%s' % (JFS.JFS_ROOT, jfs.username) + '/Jotta/Archive/%252FVolumes%252FMedia%252Ftest.txt'
        #print clean_room_path
        #print jfs_f.path
        assert jfs.session.get(clean_room_path).status_code == 200 # check that strange file name is preserved
        assert jfs_f.path == clean_room_path
        jfs_f.delete()

class TestJFSFileDirList:
    'Tests for JFSFileDirList'

    def test_api(self):
        fdl = jfs.getObject('/Jotta/Sync/?mode=list')
        assert isinstance(fdl, JFS.JFSFileDirList)
        assert len(fdl.tree) > 0

class TestJFSError:
    'Test different JFSErrors'
    """
    class JFSError(Exception):
    class JFSBadRequestError(JFSError): # HTTP 400
    class JFSCredentialsError(JFSError): # HTTP 401
    class JFSNotFoundError(JFSError): # HTTP 404
    class JFSAccessError(JFSError): #
    class JFSAuthenticationError(JFSError): # HTTP 403
    class JFSServerError(JFSError): # HTTP 500
    class JFSRangeError(JFSError): # HTTP 416
    """
    def test_errors(self):
        with pytest.raises(JFS.JFSCredentialsError): # HTTP 401
            JFS.JFS('pytest', 'pytest')
        with pytest.raises(JFS.JFSNotFoundError): # HTTP 404
            jfs.get('/Jotta/Archive/FileNot.found')
        with pytest.raises(JFS.JFSRangeError): # HTTP 416
            p = "/Jotta/Archive/testfile_up_and_readpartial.txt"
            t = jfs.up(p, StringIO.StringIO(TESTFILEDATA))
            f = jfs.getObject(p)
            f.readpartial(10, 3) # Range start index larger than end index;
            f.delete()


"""
TODO
class JFSFolder(object):
class ProtoFile(object):
class JFSIncompleteFile(ProtoFile):
class JFSFile(JFSIncompleteFile):
class JFSMountPoint(JFSFolder):
class JFSDevice(object):
class JFSenableSharing(object):
"""
