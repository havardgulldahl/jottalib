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

TESTFILEDATA="""
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla est dolor, convallis fermentum sapien in, fringilla congue ligula. Fusce at justo ac felis vulputate laoreet vel at metus. Aenean justo lacus, porttitor dignissim imperdiet a, elementum cursus ligula. Vivamus eu est viverra, pretium arcu eget, imperdiet eros. Curabitur in bibendum."""


def hack_sysargv(*newargs):
    sys.argv = list(sys.argv[0], *newargs)


def test_get_jotta_device():
    jfs = JFS.JFS()
    dev = cli.get_jotta_device(jfs)
    assert isinstance(dev, JFS.JFSDevice)
    assert dev.name == 'Jotta'

def test_get_root_dir():
    jfs = JFS.JFS()
    root = cli.get_root_dir(jfs)
    assert isinstance(root, JFS.JFSMountPoint)

def test_ls():
    cli.ls()
    hack_sysargv(['--all'])
    cli.ls()

def test_mkdir():
    hack_sysargv(['mkdir', 'testmkdir'])
    cli.mkdir()


def test_monitor():
    cli.monitor()

def test_scanner():
    cli.scanner()

def test_fuse():
    cli.fuse()

# TODO:

# def parse_args_and_apply_logging_level(parser):
# def print_size(num, humanize=False):
# def fuse():
# def upload():
# def share():
# def download():
# def rm():
# def restore():
# def scanner():
# def monitor():
