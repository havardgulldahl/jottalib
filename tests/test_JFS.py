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
import os, logging, datetime
import tempfile, posixpath, urllib
import six
from six.moves import cStringIO as StringIO


# import dependencies
import lxml
import dateutil
import requests

# import py.test
import pytest # pip install pytest

# import jotta
from jottalib import JFS, __version__

jfs = JFS.JFS() # get username and password from environment or .netrc


TESTFILEDATA=b"""
Lørem ipsum dolor sit amet, consectetur adipiscing elit. Nulla est dolor, convallis fermentum sapien in, fringilla congue ligula. Fusce at justo ac felis vulputate laoreet vel at metus. Aenean justo lacus, porttitor dignissim imperdiet a, elementum cursus ligula. Vivamus eu est viverra, pretium arcu eget, imperdiet eros. Curabitur in bibendum."""


class TestJFS:
    def test_xml(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>

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
        t = jfs.up(p, six.BytesIO(TESTFILEDATA))
        assert isinstance(t, JFS.JFSFile)
        d = t.delete()
        assert isinstance(d, JFS.JFSFile)
        assert d.is_deleted()

    def test_up_and_read(self):
        p = "/Jotta/Archive/testfile_up_and_read.txt"
        t = jfs.up(p, six.BytesIO(TESTFILEDATA))
        f = jfs.getObject(p)
        assert isinstance(f, JFS.JFSFile)
        assert f.read() == TESTFILEDATA
        f.delete()

    def test_up_and_readpartial(self):
        import random
        p = "/Jotta/Archive/testfile_up_and_readpartial.txt"
        t = jfs.up(p, six.BytesIO(TESTFILEDATA))
        f = jfs.getObject(p)
        # pick a number less than length of text
        start = random.randint(0, len(TESTFILEDATA))
        # pick a number between start and length of text
        end = random.randint(0, len(TESTFILEDATA)-start) + start
        assert f.readpartial(start, end) == TESTFILEDATA[start:end]
        f.delete()

    def test_stream(self):
        p = "/Jotta/Archive/testfile_up_and_stream.txt"
        t = jfs.up(p, six.BytesIO(TESTFILEDATA))
        s = b"".join( [ chunk for chunk in t.stream() ] )
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
            if six.PY2:
                _f = tempfile.NamedTemporaryFile(mode='w+', prefix=f)
            elif six.PY3:
                _f = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', prefix=f)
            _f.write('123test')
            jfs_f = jfs.up(p, _f)
            clean_room_path = '%s%s%s%s' % (JFS.JFS_ROOT, jfs.username, '/Jotta/Archive/', f)
            assert jfs.session.get(clean_room_path).status_code == 200 # check that strange file name is preserved
            assert jfs_f.path == clean_room_path
            jfs_f.delete()

class TestJFSDevice:

    def test_xml(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>

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
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>

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
        assert all(isinstance(item, (JFS.JFSFile, JFS.JFSIncompleteFile)) for item in dev.files())
        assert all(isinstance(item, JFS.JFSFolder) for item in dev.folders())
        newf = dev.mkdir('testdir')
        assert isinstance(newf, JFS.JFSFolder)
        newf.delete()

        _f = tempfile.NamedTemporaryFile()
        _f.write(u'123test')

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
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>

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

    def test_image(self):
        #test image stuff
        # image data
        JPEG = tempfile.NamedTemporaryFile(suffix='.jpg')
        JPEG.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xfe\x00>CREATOR: gd-jpeg v1.0 (using IJG JPEG v80), default quality\n\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xdb\x00C\x01\t\t\t\x0c\x0b\x0c\x18\r\r\x182!\x1c!22222222222222222222222222222222222222222222222222\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xc4\x00\x1f\x01\x00\x03\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x11\x00\x02\x01\x02\x04\x04\x03\x04\x07\x05\x04\x04\x00\x01\x02w\x00\x01\x02\x03\x11\x04\x05!1\x06\x12AQ\x07aq\x13"2\x81\x08\x14B\x91\xa1\xb1\xc1\t#3R\xf0\x15br\xd1\n\x16$4\xe1%\xf1\x17\x18\x19\x1a&\'()*56789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xf7\xfa(\xa2\x80?\xff\xd9')

        folder = jfs.getObject('/Jotta/Archive')
        img = folder.up(JPEG)
        assert img.is_image() == True
        assert img.thumb(size=JFS.JFSFile.BIGTHUMB) is not None
        assert img.thumb(size=JFS.JFSFile.XLTHUMB) is not None
        assert img.thumb(size=JFS.JFSFile.MEDIUMTHUMB) is not None
        assert img.thumb(size=JFS.JFSFile.SMALLTHUMB) is not None

        img.delete()
        #TODO: test file operations: .stream(), .rename(), .read(), .read_partial, .delete etc
        #TODO: test revisions

    @pytest.mark.xfail # TODO: figure out the best API for writing unicode strings
    def test_unicode_contents(self):
        data = six.StringIO(u'123abcæøå')
        p = "/Jotta/Archive/testfile_unicode_contents.txt"
        t = jfs.up(p, data)
        assert isinstance(JFSFile, t)
        t.delete()

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
            t = jfs.up(p, six.BytesIO(TESTFILEDATA))
            f = jfs.getObject(p)
            f.readpartial(10, 3) # Range start index larger than end index;
            f.delete()
        # TODO raise all errors. but how?


class TestJFSFolder:
    'Tests for folders'

    def test_xml(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>

<folder name="test2" time="2015-09-28-T13:49:05Z" host="dn-091.site-000.jotta.no">
  <path xml:space="preserve">/havardgulldahl/Jotta/Archive</path>
  <abspath xml:space="preserve">/havardgulldahl/Jotta/Archive</abspath>
  <folders>
    <folder name="Documents"/>
  </folders>
  <files>
    <file name="boink.txt~" uuid="c6684726-a842-4536-95b9-140584515dd1">
      <currentRevision>
        <number>1</number>
        <state>COMPLETED</state>
        <created>2014-10-05-T10:23:18Z</created>
        <modified>2014-10-05-T10:23:18Z</modified>
        <mime>application/octet-stream</mime>
        <mstyle>APPLICATION_OCTET_STREAM</mstyle>
        <size>40</size>
        <md5>b924ebbc79ad414ded4af442ac7080d3</md5>
        <updated>2014-11-23-T21:12:47Z</updated>
      </currentRevision>
    </file>
    <file name="boink.txx~" uuid="1b243d8e-d6df-412c-a2ce-926ebaa73f47">
      <currentRevision>
        <number>1</number>
        <state>COMPLETED</state>
        <created>2014-10-05-T10:23:18Z</created>
        <modified>2014-10-05-T10:23:18Z</modified>
        <mime>application/octet-stream</mime>
        <mstyle>APPLICATION_OCTET_STREAM</mstyle>
        <size>40</size>
        <md5>0c7652132733ead903dbdb942577fed7</md5>
        <updated>2014-11-23-T21:27:21Z</updated>
      </currentRevision>
    </file>
    <file name="boink.txy~" uuid="ba1ec941-8901-4eec-b797-bde9b6b1958c">
      <currentRevision>
        <number>1</number>
        <state>COMPLETED</state>
        <created>2014-10-05-T10:23:18Z</created>
        <modified>2014-10-05-T10:23:18Z</modified>
        <mime>application/octet-stream</mime>
        <mstyle>APPLICATION_OCTET_STREAM</mstyle>
        <size>40</size>
        <md5>d32f37bf39041d9bb92ad45012e32cb9</md5>
        <updated>2014-11-23-T21:05:11Z</updated>
      </currentRevision>
    </file>
    <file name="boink.txz~" uuid="6724af96-e462-4862-b82a-00b7836a0681">
      <currentRevision>
        <number>1</number>
        <state>COMPLETED</state>
        <created>2014-10-05-T10:23:18Z</created>
        <modified>2014-10-05-T10:23:18Z</modified>
        <mime>application/octet-stream</mime>
        <mstyle>APPLICATION_OCTET_STREAM</mstyle>
        <size>9</size>
        <md5>e3a2cba90ec7630bdf1d0566c8abb93e</md5>
        <updated>2014-11-23-T21:03:25Z</updated>
      </currentRevision>
    </file>
    <file name="dingdong" uuid="95c4bbcc-9a59-4669-b4cb-ee49c186ae1b">
      <currentRevision>
        <number>127</number>
        <state>COMPLETED</state>
        <created>2014-10-05-T10:23:18Z</created>
        <modified>2014-10-05-T10:23:18Z</modified>
        <mime>application/octet-stream</mime>
        <mstyle>APPLICATION_OCTET_STREAM</mstyle>
        <size>20480</size>
        <md5>daa100df6e6711906b61c9ab5aa16032</md5>
        <updated>2014-11-23-T22:56:30Z</updated>
      </currentRevision>
    </file>
    <file name="fisk.txt" uuid="8b6db048-c44b-4656-8024-737a0c38c7ad">
      <currentRevision>
        <number>1</number>
        <state>COMPLETED</state>
        <created>2014-10-05-T10:23:18Z</created>
        <modified>2014-10-05-T10:23:18Z</modified>
        <mime>text/plain</mime>
        <mstyle>TEXT_PLAIN</mstyle>
        <size>18</size>
        <md5>308285a59ae0a4a5ede4f7a0c08d2390</md5>
        <updated>2014-11-23-T19:56:51Z</updated>
      </currentRevision>
    </file>
    <file name="nyboink.txt" uuid="3d0a0a28-4c68-4e6a-8414-fa5c37ec45cb">
      <currentRevision>
        <number>26</number>
        <state>COMPLETED</state>
        <created>2014-10-05-T10:23:18Z</created>
        <modified>2014-10-05-T10:23:18Z</modified>
        <mime>text/plain</mime>
        <mstyle>TEXT_PLAIN</mstyle>
        <size>6</size>
        <md5>6882bf1ef7f4d938a4cf2931d6953fa1</md5>
        <updated>2014-11-23-T21:28:55Z</updated>
      </currentRevision>
    </file>
    <file name="oo.txt" uuid="691aa9b6-eec1-4564-803e-6288dc57aa37">
      <currentRevision>
        <number>3</number>
        <state>COMPLETED</state>
        <created>2014-12-18-T21:23:48Z</created>
        <modified>2014-12-18-T21:23:48Z</modified>
        <mime>text/plain</mime>
        <mstyle>TEXT_PLAIN</mstyle>
        <size>4</size>
        <md5>aa3f5bb8c988fa9b75a1cdb1dc4d93fc</md5>
        <updated>2014-12-18-T21:23:48Z</updated>
      </currentRevision>
    </file>
    <file name="pingpong.data" uuid="f02f1ca1-c6a4-403d-b344-f4e3417d92fd">
      <currentRevision>
        <number>165</number>
        <state>COMPLETED</state>
        <created>2014-12-18-T21:20:32Z</created>
        <modified>2014-12-18-T21:20:32Z</modified>
        <mime>application/octet-stream</mime>
        <mstyle>APPLICATION_OCTET_STREAM</mstyle>
        <size>9216</size>
        <md5>ec041186ebff92a26ab3ef2dd34dd0e7</md5>
        <updated>2014-12-18-T21:20:32Z</updated>
      </currentRevision>
    </file>
    <file name="testfs" uuid="a00034dd-971c-4699-8ee0-e7514045770e">
      <currentRevision>
        <number>2</number>
        <state>COMPLETED</state>
        <created>2014-10-05-T10:23:18Z</created>
        <modified>2014-10-05-T10:23:18Z</modified>
        <mime>application/octet-stream</mime>
        <mstyle>APPLICATION_OCTET_STREAM</mstyle>
        <size>0</size>
        <md5>d41d8cd98f00b204e9800998ecf8427e</md5>
        <updated>2014-11-23-T19:41:03Z</updated>
      </currentRevision>
    </file>
  </files>
  <metadata first="" max="" total="11" num_folders="1" num_files="10"/>
</folder>
"""
        o = lxml.objectify.fromstring(xml)
        dev = JFS.JFSFolder(o, jfs, parentpath=jfs.rootpath + '/Jotta/Archive')
        dev.synced = True # make sure our tests are based on the xml above, and not live

        #test native properties
        assert dev.path == jfs.rootpath + '/Jotta/Archive/test2'
        assert dev.name == 'test2'
        assert dev.deleted == None
        assert dev.is_deleted() == False

        #test convenience methods
        assert len(list(dev.folders())) == 1
        assert len(list(dev.files())) == 10
        assert all(isinstance(item, JFS.JFSFile) for item in dev.files())
        assert all(isinstance(item, JFS.JFSFolder) for item in dev.folders())


    @pytest.mark.xfail  # TODO: restore this when bug #74 is squashed
    def test_delete_and_restore():
        # testing jottacloud delete and restore
        dev = jfs.getObject('/Jotta/Sync')
        newf = dev.mkdir('testdir')
        assert isinstance(newf, JFS.JFSFolder)
        oldf = newf.delete()
        assert isinstance(oldf, JFS.JFSFolder)
        assert oldf.is_deleted() == True
        assert isinstance(oldf.deleted, datetime.datetime)
        restoredf = oldf.restore()
        assert isinstance(restoredf, JFS.JFSFolder)
        assert restoredf.is_deleted() == False
        purgedf = restoredf.hard_delete()


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







"""
TODO
class JFSIncompleteFile(ProtoFile):
class JFSenableSharing(object):
"""
