#!/usr/bin/env python
# -*- coding: utf-8

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "tools"))
from jottacloudclientmonitor import ArchiveEventHandler

def test_correct_url(tmpdir):
    tmpdir = str(tmpdir)
    aeh = ArchiveEventHandler(None, tmpdir, "/TEST_ROOT")
    filepath = os.path.join(tmpdir, "subdir", "correct_url.txt")
    jottapath = aeh.get_jottapath(filepath)
    assert jottapath == "/TEST_ROOT/subdir/correct_url.txt"

def test_weird_path_is_correct_url(tmpdir):
    tmpdir = str(tmpdir)
    aeh = ArchiveEventHandler(None, tmpdir, "/TEST_ROOT")
    filepath = os.path.join(tmpdir, "subdir1", "..", "subdir2", "correct_url.txt")
    jottapath = aeh.get_jottapath(filepath)
    assert jottapath == "/TEST_ROOT/subdir2/correct_url.txt"

def test_filename_renamed(tmpdir):
    tmpdir = str(tmpdir)
    aeh = ArchiveEventHandler(None, tmpdir, "/TEST_ROOT")
    filepath = os.path.join(tmpdir, "subdir", "first_url.txt")
    jottapath = aeh.get_jottapath(filepath, "correct_url.txt")
    assert jottapath == "/TEST_ROOT/subdir/correct_url.txt"
