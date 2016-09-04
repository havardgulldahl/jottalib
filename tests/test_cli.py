# -*- encoding: utf-8 -*-
'Tests for jottalib/cli.py'
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
# along with jottalib.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2015 Håvard Gulldahl <havard@gulldahl.no>

# metadata
__author__ = 'havard@gulldahl.no'

# import standardlib
import os, sys, logging, random, hashlib
import os.path, posixpath, zipfile
from datetime import datetime

from six import StringIO

# import py.test
import pytest # pip install pytest

# import jotta
from jottalib import JFS, __version__, cli

WIN32 = (sys.platform == "win32")

TESTFILEDATA=u"""
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla est dolor, convallis fermentum sapien in, fringilla congue ligula. Fusce at justo ac felis vulputate laoreet vel at metus. Aenean justo lacus, porttitor dignissim imperdiet a, elementum cursus ligula. Vivamus eu est viverra, pretium arcu eget, imperdiet eros. Curabitur in bibendum."""

EPOCH = datetime(1970, 1, 1)

def timestamp():
    """
    :return: now in unix time, eg. seconds since 1970
    """
    return (datetime.utcnow() - EPOCH).total_seconds()

jfs = JFS.JFS()
dev = cli.get_jfs_device(jfs)
root = cli.get_root_dir(jfs)

def test_get_jotta_device():
    assert isinstance(dev, JFS.JFSDevice)
    assert dev.name == 'Jotta'

def test_get_root_dir():
    assert isinstance(root, JFS.JFSMountPoint)

def test_ls():
    assert cli.ls([])
    assert cli.ls(['--all'])
    assert cli.ls(['--humanize'])
    assert cli.ls(['--loglevel', 'info'])

def test_mkdir():
    with pytest.raises(SystemExit):
        cli.mkdir([]) # argparse should raise systemexit without the mandatory arguments
    assert cli.mkdir(['testmkdir'])
    d = jfs.getObject('/Jotta/Sync/testmkdir')
    assert isinstance(d, JFS.JFSFolder)
    assert d.is_deleted() == False

def test_upload(tmpdir):
    with pytest.raises(SystemExit):
        cli.upload([]) # argparse should raise systemexit without the mandatory arguments

    testfile = tmpdir.join('test_upload-%s.txt' % timestamp()).ensure()
    testfile.write(TESTFILEDATA)
    assert cli.upload([str(testfile), '//Jotta/Archive'])
    fi = jfs.getObject('/Jotta/Archive/%s' % str(testfile.basename))
    assert isinstance(fi, JFS.JFSFile)
    assert fi.read() == TESTFILEDATA
    fi.delete()

def test_upload_crazy_filenames(tmpdir):
    # test crazy filenames
    jotta_test_path = '//Jotta/Archive/crazyfilename'
    cli.mkdir([jotta_test_path])
    zip = zipfile.ZipFile('tests/crazyfilenames.zip')
    zip.extractall(path=str(tmpdir))
    for crazyfilename in tmpdir.join('crazyfilenames').listdir():
        _filename = crazyfilename.basename
        _base, _enc, _ext = _filename.split('.') 
        assert cli.upload([str(crazyfilename), jotta_test_path])
        # TODO: enable this
        #assert cli.cat([os.path.join(jotta_test_path, _filename), ]) == crazyfilename.read()
    cli.rm([jotta_test_path])

def test_rm():
    with pytest.raises(SystemExit):
        cli.rm([]) # argparse should raise systemexit without the mandatory arguments
    assert cli.rm(['testmkdir'])
    d = jfs.getObject('/Jotta/Sync/testmkdir')
    assert isinstance(d, JFS.JFSFolder)
    assert d.is_deleted() == True

def test_cat():
    with pytest.raises(SystemExit):
        cli.cat([]) # argparse should raise systemexit without the mandatory arguments
    testcontents = u'12345test'
    testpath = '/Jotta/Archive/Test/test.txt'
    d = jfs.up(testpath, StringIO(testcontents))
    assert isinstance(d, JFS.JFSFile)
    assert cli.cat(['/%s' % testpath,]) == testcontents


@pytest.mark.xfail(raises=NotImplementedError)
def test_restore():
    with pytest.raises(SystemExit):
        cli.rm([]) # argparse should raise systemexit without the mandatory arguments
    assert cli.mkdir(['testmkdir'])
    assert cli.rm(['testmkdir'])
    assert cli.restore(['testmkdir'])
    d = jfs.getObject('/Jotta/Sync/testmkdir')
    assert isinstance(d, JFS.JFSFolder)
    assert d.is_deleted() == False


def test_monitor():
    with pytest.raises(SystemExit):
        cli.monitor([]) # argparse should raise systemexit without the mandatory arguments


def test_scanner():
    with pytest.raises(SystemExit):
        cli.scanner([]) # argparse should raise systemexit without the mandatory arguments

def test_fuse():
    with pytest.raises(SystemExit):
        cli.fuse([]) # argparse should raise systemexit without the mandatory arguments


def test_download(tmpdir):
    with pytest.raises(SystemExit):
        cli.download([]) # argparse should raise systemexit without the mandatory arguments
    testcontents = u'12345test'
    testdir = '/Jotta/Archive/Test'
    testfile = 'test.txt'
    testpath = posixpath.join(testdir, testfile)
    d = jfs.up(testpath, StringIO(testcontents))
    with tmpdir.as_cwd():
        assert cli.download(['/%s' % testpath,])
        assert cli.download(['/%s' % testpath, '--checksum'])
        #TODO: implement when --resume is - assert cli.download(['/%s' % testpath, '--resume'])
        assert tmpdir.join(testfile).read_text('utf-8') == testcontents
        # download the whole directlry
        assert cli.download(['/%s' % testdir,])
        assert cli.download(['/%s' % testdir, '--checksum'])
        assert tmpdir.join('Test').join(testfile).read() == testcontents

# TODO:

# def parse_args_and_apply_logging_level(parser):
# def print_size(num, humanize=False):
# def upload():
# def share():
# def scanner():
# def monitor():
