# -*- encoding: utf-8 -*-
'Tests for jottacloud.py'
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
import os, logging, tempfile, random, hashlib
try:
    from io import StringIO # py3
except ImportError:
    from cStringIO import StringIO  # py2

# import py.test
import pytest # pip install pytest

try:
    from xattr import xattr # pip install xattr
    HAS_XATTR=True
except ImportError: # no xattr installed, not critical because it is optional
    HAS_XATTR=False


# import jotta
from jottalib import JFS, __version__, jottacloud


jfs = JFS.JFS() # get username and password from environment or .netrc


TESTFILEDATA="""
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla est dolor, convallis fermentum sapien in, fringilla congue ligula. Fusce at justo ac felis vulputate laoreet vel at metus. Aenean justo lacus, porttitor dignissim imperdiet a, elementum cursus ligula. Vivamus eu est viverra, pretium arcu eget, imperdiet eros. Curabitur in bibendum."""

class TestXattr:

    @pytest.mark.skipif(HAS_XATTR==False,
                        reason="requires xattr")
    def test_setget(self):
        temp = tempfile.NamedTemporaryFile()
        temp.write(random.randint(0, 10)*TESTFILEDATA)
        temp.flush()
        temp.seek(0)
        md5 = hashlib.md5(temp.read()).hexdigest()
        assert jottacloud.setxattrhash(temp.name, md5) is not False
        assert jottacloud.getxattrhash(temp.name) == md5
        x = xattr(temp.name)
        assert x.get('user.jottalib.md5') == md5
        assert x.get('user.jottalib.filesize') == str(os.path.getsize(temp.name)) # xattr always stores strings


def test_get_jottapath(tmpdir):
    topdir = tmpdir.mkdir("topdir")
    subdir = topdir.mkdir("subdir1").mkdir("subdir2")
    jottapath = jottacloud.get_jottapath(str(topdir), str(subdir), "/TEST_ROOT")
    assert jottapath == "/TEST_ROOT/topdir/subdir1/subdir2"

# TODO:
# def get_jottapath(localtopdir, dirpath, jottamountpoint):
# def is_file(jottapath, JFS):
# def filelist(jottapath, JFS):
# def compare(localtopdir, jottamountpoint, JFS, followlinks=False, exclude_patterns=None):
# def _decode_filename(f):
# def new(localfile, jottapath, JFS):
# def resume(localfile, jottafile, JFS):
# def replace_if_changed(localfile, jottapath, JFS):
# def delete(jottapath, JFS):
# def mkdir(jottapath, JFS):
# def iter_tree(jottapath, JFS):

