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
import os, logging, tempfile, random, hashlib, stat
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
    # def get_jottapath(localtopdir, dirpath, jottamountpoint):
    topdir = tmpdir.mkdir("topdir")
    subdir = topdir.mkdir("subdir1").mkdir("subdir2")
    jottapath = jottacloud.get_jottapath(str(topdir), str(subdir), "/TEST_ROOT")
    assert jottapath == "/TEST_ROOT/topdir/subdir1/subdir2"


def test_new():
    # def new(localfile, jottapath, JFS):
    _localfile = u'tests/crazyfilenames/easy.ascii.txt'
    _jottapath = u'/Jotta/Archive/TEST/test_new_ascii_filename.txt'
    _new = jottacloud.new(_localfile, _jottapath, jfs)
    assert isinstance(_new, JFS.JFSFile)
    _new.delete()
    _localfile2 = u'tests/crazyfilenames/blåbær.utf8.txt'
    _jottapath2 = u'/Jotta/Archive/TEST/test_new_blåbær_utf8_filename.txt'
    _new2 = jottacloud.new(_localfile2, _jottapath2, jfs)
    assert isinstance(_new2, JFS.JFSFile)
    assert _new2.path.endswith(_jottapath2)
    _new2.delete()


def test_is_file():
    # def is_file(jottapath, JFS):
    _localfile = u'tests/crazyfilenames/easy.ascii.txt'
    _jottapath = u'/Jotta/Archive/TEST/test_is_file.txt'
    _new = jottacloud.new(_localfile, _jottapath, jfs)
    assert jottacloud.is_file(_jottapath, jfs)
    _new.delete()


def test_delete():
    # def delete(jottapath, JFS):
    _localfile = u'tests/crazyfilenames/easy.ascii.txt'
    _jottapath = u'/Jotta/Archive/TEST/test_delete.txt'
    _new = jottacloud.new(_localfile, _jottapath, jfs)
    _del = _new.delete()
    assert _del.is_deleted() == True

def test_replace_if_changed():
    # def replace_if_changed(localfile, jottapath, JFS):
    # first test non-existing jottapath
    # it should raise a not found JFSNotFoundError
    _localfile = u'tests/crazyfilenames/easy.ascii.txt'
    rndm = random.randint(0, 1000)
    with pytest.raises(JFS.JFSNotFoundError):
        assert jottacloud.replace_if_changed(_localfile,
                                             '/Jotta/Archive/test_replace_if_changed_nonexisting-%i.txt' % rndm,
                                             jfs)
    # now, put some data there and uplaod
    _localfile = tempfile.NamedTemporaryFile() # auto close, auto delete on out of scope
    _localfilepath = _localfile.name
    _localfile.write(1*TESTFILEDATA)
    _localfile.flush()
    _localfile.seek(0)
    _jottapath = u'/Jotta/Archive/TEST/test_replace_if_changed.txt'
    assert jottacloud.new(_localfilepath, _jottapath, jfs)
    # lastly, edit data, and see if it is automatically reuploaded
    newdata = 2*TESTFILEDATA
    _localfile.write(newdata)
    _localfile.flush()
    jottacloud.replace_if_changed(_localfilepath, _jottapath, jfs)
    cloudobj = jfs.getObject(_jottapath)
    assert cloudobj.read() == newdata
    _del = cloudobj.delete()

def test_special_files(tmpdir):
    # FIFO
    os.mkfifo(str(tmpdir.join('fifo')))
    # Block device
    try:
        os.mknod(str(tmpdir.join('blck')), 0o600 | stat.S_IFBLK, os.makedev(10, 20))
    except OSError as e:
        pass
    # Char device
    try:
        os.mknod(str(tmpdir.join('char')), 0o600 | stat.S_IFCHR, os.makedev(30, 40))
    except OSError as e:
        pass
    # add some control group files
    tmpdir.join('control1').write('control1', ensure=True)
    tmpdir.join('control2.txt').write('control2.txt', ensure=True)

    _jottapath = u'/Jotta/Archive/TEST_SPECIAL'
    #def compare(localtopdir, jottamountpoint, JFS, followlinks=False, exclude_patterns=None):
    # dirpath, # byte string, full path
    #    onlylocal, # set(), files that only exist locally, i.e. newly added files that don't exist online,
    #    onlyremote, # set(), files that only exist in the JottaCloud, i.e. deleted locally
    #    bothplaces # set(), files that exist both locally and remotely
    #    onlyremotefolders,

    tree = list(jottacloud.compare(str(tmpdir), _jottapath, jfs))
    _, onlylocal, _, _, _ = tree[0]
    assert len(onlylocal) == 2
    for _basename in [os.path.basename(x.localpath) for x in onlylocal]:
        assert _basename in ('control1', 'control2.txt')



# TODO:
# def filelist(jottapath, JFS):
# def compare w exclude_patterns
# def resume(localfile, jottafile, JFS):
# def mkdir(jottapath, JFS):
# def iter_tree(jottapath, JFS):

