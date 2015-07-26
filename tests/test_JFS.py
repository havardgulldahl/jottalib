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
import os, StringIO


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
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla est dolor, convallis fermentum sapien in, fringilla congue ligula. Fusce at justo ac felis vulputate laoreet vel at metus. Aenean justo lacus, porttitor dignissim imperdiet a, elementum cursus ligula. Vivamus eu est viverra, pretium arcu eget, imperdiet eros. Curabitur in bibendum.

"""


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
        assert isinstance(t, JFS.JFSFile)
        assert t.is_deleted() == True

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
        start = random.randint(0, len(TESTFILEDATA))
        end = random.randint(0, len(TESTFILEDATA)-start)
        assert f.readpartial(start, end) == TESTFILEDATA[start:end]
        f.delete()

    def test_stream(self):
        pass

    def test_resume(self):
        pass


    def test_post(self):
        pass
        #TODO: test unicode string upload
        #TODO: test file list upload
        #TODO: test upload_callback

    def test_getObject(self):

        assert isinstance(jfs.getObject('/Jotta'), JFS.JFSDevice)
        assert isinstance(jfs.getObject('/Jotta/Archive'), JFS.JFSMountPoint)
        assert isinstance(jfs.getObject('/Jotta/Archive/test'), JFS.JFSFolder)
        assert isinstance(jfs.getObject('/Jotta/Archive/test?mode=list'), JFS.JFSFileDirList)


        #TODO: test with a python-requests object