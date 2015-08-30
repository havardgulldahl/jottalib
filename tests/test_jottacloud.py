#!/usr/bin/env python
# -*- coding: utf-8

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "tools"))
from jottacloudclient import jottacloud

def test_get_jottapath(tmpdir):
    topdir = tmpdir.mkdir("topdir")
    subdir = topdir.mkdir("subdir1").mkdir("subdir2")
    jottapath = jottacloud.get_jottapath(str(topdir), str(subdir), "/TEST_ROOT")
    assert jottapath == "/TEST_ROOT/topdir/subdir1/subdir2"
