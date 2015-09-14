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
import os, StringIO, logging, datetime
import tempfile, posixpath, urllib

# import dependencies
import lxml
import dateutil
import requests

# import py.test
import pytest # pip install pytest

# import jotta
from jottalib import JFS, __version__

jfs = JFS.JFS() # get username and password from environment or .netrc


TESTFILEDATA="""
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla est dolor, convallis fermentum sapien in, fringilla congue ligula. Fusce at justo ac felis vulputate laoreet vel at metus. Aenean justo lacus, porttitor dignissim imperdiet a, elementum cursus ligula. Vivamus eu est viverra, pretium arcu eget, imperdiet eros. Curabitur in bibendum."""


class TestJFS:
    def test_xml(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>

<user time="2015-09-12-T23:14:23Z" host="dn-093.site-000.jotta.no">
  <username>havardgulldahl</username>
  <account-type>unlimited</account-type>
  <locked>false</locked>
  <capacity>-1</capacity>
  <max-devices>-1</max-devices>
  <max-mobile-devices>-1</max-mobile-devices>
  <usage>2039672393219</usage>
  <read-locked>false</read-locked>
  <write-locked>false</write-locked>
  <quota-write-locked>false</quota-write-locked>
  <enable-sync>true</enable-sync>
  <enable-foldershare>true</enable-foldershare>
  <devices>
    <device>
      <name xml:space="preserve">My funky iphone</name>
      <type>IPHONE</type>
      <sid>0d015a5b-c2e6-46b3-9df8-00269c35xxxx</sid>
      <size>4280452534</size>
      <modified>2015-01-04-T08:03:09Z</modified>
    </device>
    <device>
      <name xml:space="preserve">My funky ipad</name>
      <type>IPAD</type>
      <sid>a179ffb0-23a1-48ca-89bc-e92a571xxxxx</sid>
      <size>4074923911</size>
      <modified>2015-08-06-T05:34:39Z</modified>
    </device>
    <device>
      <name xml:space="preserve">My funky laptop</name>
      <type>LAPTOP</type>
      <sid>a018410c-f00b-49ff-aab8-18b7a50xxxxx</sid>
      <size>159113667199</size>
      <modified>2015-09-12-T23:14:02Z</modified>
    </device>
  </devices>
</user>"""



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
        tests = ['%2FVolumes%2FMedia%2Ftest.txt', # existing percent encoding, see #25
                 'My funky file.txt', # file name with spaces, see 57
                 'My+funky+file.txt', # file name with plus signs
                 'My?funky?file.txt', # file name with question marks
                 'My=funky=file.txt', # file name with equal signs
                 'My&funky&file.txt', # file name with ampersand signs
                 'My#funky#file.txt', # file name with pound signs
                 'My:funky:file.txt', # file name with colon signs
                 'My@funky@file.txt', # file name with at signs
                 'My;funky;file.txt', # file name with semi-colon signs
                 'My$funky$file.txt', # file name with dollar signs
                 'My%funky%file.txt', # file name with per cent signs
                 'My,funky,file.txt', # file name with commas
                ]
        for f in tests:
            p = posixpath.join('/Jotta/Archive', f)
            _f = tempfile.NamedTemporaryFile(prefix=f)
            _f.write('123test')
            jfs_f = jfs.up(p, _f)
            clean_room_path = '%s%s%s%s' % (JFS.JFS_ROOT, jfs.username, '/Jotta/Archive/', f)
            assert jfs.session.get(clean_room_path).status_code == 200 # check that strange file name is preserved
            assert jfs_f.path == clean_room_path
            jfs_f.delete()

class TestJFSDevice:

    def test_xml(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>

<device time="2015-09-12-T23:14:25Z" host="dn-093.site-000.jotta.no">
  <name xml:space="preserve">Jotta</name>
  <type>JOTTA</type>
  <sid>ee93a510-907a-4d7c-bbb9-59df7894xxxx</sid>
  <size>58428516774</size>
  <modified>2015-09-12-T23:10:51Z</modified>
  <user>havardgulldahl</user>
  <mountPoints>
    <mountPoint>
      <name xml:space="preserve">Archive</name>
      <size>18577011381</size>
      <modified>2015-09-12-T23:10:51Z</modified>
    </mountPoint>
    <mountPoint>
      <name xml:space="preserve">Shared</name>
      <size>43777</size>
      <modified>2015-09-03-T21:12:55Z</modified>
    </mountPoint>
    <mountPoint>
      <name xml:space="preserve">Sync</name>
      <size>39851461616</size>
      <modified>2015-07-26-T22:26:54Z</modified>
    </mountPoint>
  </mountPoints>
  <metadata first="" max="" total="3" num_mountpoints="3"/>
</device>"""
        o = lxml.objectify.fromstring(xml)
        dev = JFS.JFSDevice(o, jfs, parentpath=jfs.rootpath)
        assert isinstance(o, lxml.objectify.ObjectifiedElement)
        # Test that mountpoints are populated correctly"
        assert sorted(dev.mountPoints.keys()) == ['Archive', 'Shared', 'Sync']
        assert all(isinstance(item, JFS.JFSMountPoint) for item in dev.mountPoints.values())
        # test "mountPoint" may be either an actual mountPoint element from JFSDevice.mountPoints{} or its .name. '
        assert all(isinstance(item, JFS.JFSFile) for item in dev.files('Archive'))
        # test "mountPoint" may be either an actual mountPoint element from JFSDevice.mountPoints{} or its .name. '
        mps = dev.mountpointobjects()
        assert all(isinstance(item, JFS.JFSFile) for item in dev.files(mps[2]))

        #test "mountPoint" may be either an actual mountPoint element from JFSDevice.mountPoints{} or its .name. '
        assert all(isinstance(item, JFS.JFSFolder) for item in dev.folders('Archive'))
        #test "mountPoint" may be either an actual mountPoint element from JFSDevice.mountPoints{} or its .name. '
        mps = dev.mountpointobjects()
        assert all(isinstance(item, JFS.JFSFolder) for item in dev.folders(mps[0]))

        # test_properties
        assert isinstance(dev.modified, datetime.datetime)
        assert dev.path == '%s/%s' % (jfs.rootpath, 'Jotta')
        assert dev.name == 'Jotta'
        assert dev.type == 'JOTTA'
        assert dev.size == 58428516774
        assert dev.sid == 'ee93a510-907a-4d7c-bbb9-59df7894xxxx'


class TestJFSMountPoint:

    def test_xml(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>

<mountPoint time="2015-09-13-T00:16:31Z" host="dn-097.site-000.jotta.no">
  <name xml:space="preserve">Sync</name>
  <path xml:space="preserve">/havardgulldahl/Jotta</path>
  <abspath xml:space="preserve">/havardgulldahl/Jotta</abspath>
  <size>39851461616</size>
  <modified>2015-07-26-T22:26:54Z</modified>
  <device>Jotta</device>
  <user>havardgulldahl</user>
  <folders>
    <folder name="folder1"/>
    <folder name="folder2"/>
    <folder name="folder3"/>
    <folder name="folder4"/>
    <folder name="folder5"/>
    <folder name="folder6"/>
    <folder name="folder7"/>
  </folders>
  <files>
    <file name="bigfile" uuid="7a36a217-88d5-4804-99df-bbc42eb4a9f2">
      <latestRevision>
        <number>1</number>
        <state>INCOMPLETE</state>
        <created>2015-05-29-T09:02:53Z</created>
        <modified>2015-05-29-T09:02:53Z</modified>
        <mime>application/octet-stream</mime>
        <mstyle>APPLICATION_OCTET_STREAM</mstyle>
        <md5>4d710d3a12699730976216836a5217a8</md5>
        <updated>2015-05-29-T09:02:53Z</updated>
      </latestRevision>
    </file>
    <file name="test.pdf" uuid="1caec763-2ed0-4e88-9d3c-650f3babecc4">
      <currentRevision>
        <number>3</number>
        <state>COMPLETED</state>
        <created>2015-07-26-T22:26:54Z</created>
        <modified>2015-07-26-T22:26:54Z</modified>
        <mime>application/pdf</mime>
        <mstyle>APPLICATION_PDF</mstyle>
        <size>116153</size>
        <md5>138396327a51ea6bf20caa72cf6d6667</md5>
        <updated>2015-07-26-T22:26:54Z</updated>
      </currentRevision>
    </file>
  </files>
  <metadata first="" max="" total="9" num_folders="7" num_files="2"/>
</mountPoint>"""
        o = lxml.objectify.fromstring(xml)
        dev = JFS.JFSMountPoint(o, jfs, parentpath=jfs.rootpath + '/Jotta')

        #test native properties
        assert dev.name == 'Sync'
        assert dev.size == 39851461616
        assert isinstance(dev.modified, datetime.datetime)
        assert dev.modified == datetime.datetime(2015, 7, 26, 22, 26, 54).replace(tzinfo=dateutil.tz.tzutc())

        with pytest.raises(JFS.JFSError):
            dev.delete()
            dev.rename('sillywalkministry')

        # test JFSFolder inheritance
        assert dev.path == jfs.rootpath + '/Jotta/Sync'
        assert dev.deleted == None
        assert dev.is_deleted() == False
        assert all(isinstance(item, JFS.JFSFile) for item in dev.files())
        assert all(isinstance(item, JFS.JFSFolder) for item in dev.folders())
        newf = dev.mkdir('testdir')
        assert isinstance(newf, JFS.JFSFolder)
        newf.delete()

        _f = tempfile.NamedTemporaryFile()
        _f.write('123test')

        newfile = dev.up(_f)
        assert isinstance(newfile, JFS.JFSFile)
        newfile.delete()
        newfile = dev.up(_f, filename='heyhei123.txt')
        assert isinstance(newfile, JFS.JFSFile)
        assert newfile.name == 'heyhei123.txt'
        newfile.delete()
        assert isinstance(dev.filedirlist(), JFS.JFSFileDirList)

class TestJFSFile:

    def test_xml(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>

<file name="testimage.jpg" uuid="9ebcfe1a-98b1-4e38-a73e-f498555da865" time="2015-09-13-T21:22:46Z" host="dn-094.site-000.jotta.no">
  <path xml:space="preserve">/havardgulldahl/Jotta/Archive</path>
  <abspath xml:space="preserve">/havardgulldahl/Jotta/Archive</abspath>
  <currentRevision>
    <number>5</number>
    <state>COMPLETED</state>
    <created>2015-07-25-T21:18:49Z</created>
    <modified>2015-07-25-T21:18:49Z</modified>
    <mime>image/jpeg</mime>
    <mstyle>IMAGE_JPEG</mstyle>
    <size>1816221</size>
    <md5>125073533339a616b99bc53efc509561</md5>
    <updated>2015-07-25-T21:18:50Z</updated>
  </currentRevision>
  <revisions>
    <revision>
      <number>4</number>
      <state>COMPLETED</state>
      <created>2015-07-25-T21:18:05Z</created>
      <modified>2015-07-25-T21:18:05Z</modified>
      <mime>image/jpeg</mime>
      <mstyle>IMAGE_JPEG</mstyle>
      <size>1816221</size>
      <md5>125073533339a616b99bc53efc509561</md5>
      <updated>2015-07-25-T21:18:07Z</updated>
    </revision>
    <revision>
      <number>3</number>
      <state>COMPLETED</state>
      <created>2015-07-25-T21:17:49Z</created>
      <modified>2015-07-25-T21:17:49Z</modified>
      <mime>image/jpeg</mime>
      <mstyle>IMAGE_JPEG</mstyle>
      <size>1816221</size>
      <md5>125073533339a616b99bc53efc509561</md5>
      <updated>2015-07-25-T21:17:50Z</updated>
    </revision>
    <revision>
      <number>2</number>
      <state>COMPLETED</state>
      <created>2015-07-25-T21:01:45Z</created>
      <modified>2015-07-25-T21:01:45Z</modified>
      <mime>image/jpeg</mime>
      <mstyle>IMAGE_JPEG</mstyle>
      <size>1816221</size>
      <md5>125073533339a616b99bc53efc509561</md5>
      <updated>2015-07-25-T21:01:46Z</updated>
    </revision>
    <revision>
      <number>1</number>
      <state>COMPLETED</state>
      <created>2015-07-25-T21:00:02Z</created>
      <modified>2015-07-25-T21:00:02Z</modified>
      <mime>image/jpeg</mime>
      <mstyle>IMAGE_JPEG</mstyle>
      <size>1816221</size>
      <md5>125073533339a616b99bc53efc509561</md5>
      <updated>2015-07-25-T21:00:03Z</updated>
    </revision>
  </revisions>
</file>"""

        o = lxml.objectify.fromstring(xml)
        dev = JFS.JFSFile(o, jfs, parentpath=jfs.rootpath + '/Jotta/Archive')

        #test ProtoFile properties
        assert dev.path == jfs.rootpath + '/Jotta/Archive/testimage.jpg'
        assert dev.name == 'testimage.jpg'
        assert dev.uuid == '9ebcfe1a-98b1-4e38-a73e-f498555da865'
        assert dev.deleted == None
        assert dev.is_deleted() == False

        #test native properties
        assert dev.revisionNumber == 5
        assert dev.created == datetime.datetime(2015, 7, 25, 21, 18, 49).replace(tzinfo=dateutil.tz.tzutc())
        assert dev.modified == datetime.datetime(2015, 7, 25, 21, 18, 49).replace(tzinfo=dateutil.tz.tzutc())
        assert dev.updated == datetime.datetime(2015, 7, 25, 21, 18, 50).replace(tzinfo=dateutil.tz.tzutc())
        assert dev.size == 1816221
        assert dev.md5 == '125073533339a616b99bc53efc509561'
        assert dev.mime == 'image/jpeg'
        assert dev.state == 'COMPLETED'

        #test image stuff
        assert dev.is_image() == True
        assert dev.thumb(size=JFS.JFSFile.BIGTHUMB) is not None
        assert dev.thumb(size=JFS.JFSFile.XLTHUMB) is not None
        assert dev.thumb(size=JFS.JFSFile.MEDIUMTHUMB) is not None
        assert dev.thumb(size=JFS.JFSFile.SMALLTHUMB) is not None

        #TODO: test file operations: .stream(), .rename(), .read(), .read_partial, .delete etc
        #TODO: test revisions

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
            JFS.JFS(auth=('PYTEST','PYTEST'))
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
class JFSIncompleteFile(ProtoFile):
class JFSenableSharing(object):
"""
