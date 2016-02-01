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
import os, sys, logging, tempfile, random, hashlib

# import py.test
import pytest # pip install pytest

# import jotta
from jottalib import JFS, __version__, cli

TESTFILEDATA=u"""
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla est dolor, convallis fermentum sapien in, fringilla congue ligula. Fusce at justo ac felis vulputate laoreet vel at metus. Aenean justo lacus, porttitor dignissim imperdiet a, elementum cursus ligula. Vivamus eu est viverra, pretium arcu eget, imperdiet eros. Curabitur in bibendum."""

jfs = JFS.JFS()
dev = cli.get_jotta_device(jfs)
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
    assert d.is_deleted == False

def test_upload():
    with pytest.raises(SystemExit):
        cli.upload([]) # argparse should raise systemexit without the mandatory arguments
    f, filename = tempfile.mkstemp(suffix='.txt', prefix='test_upload-')
    f.write(TESTFILEDATA)
    f.close()
    assert cli.upload([filename, '.'])
    fi = jfs.getObject('/Jotta/Sync/%s' % os.path.basename(filename))
    assert isinstance(fi, JFS.JFSFile)
    assert d.is_deleted() == False
    fi.delete()

def test_rm():
    with pytest.raises(SystemExit):
        cli.rm([]) # argparse should raise systemexit without the mandatory arguments
    assert cli.rm(['testmkdir'])
    d = jfs.getObject('/Jotta/Sync/testmkdir')
    assert isinstance(d, JFS.JFSFolder)
    assert d.is_deleted() == True


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

# TODO:

# def parse_args_and_apply_logging_level(parser):
# def print_size(num, humanize=False):
# def upload():
# def share():
# def download():
# def rm():
# def restore():
# def scanner():
# def monitor():
