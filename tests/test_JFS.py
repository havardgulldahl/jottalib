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
import os


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




class TestJFS:
    def test_login(self):
        assert isinstance(jfs, JFS.JFS)


    #def test_root(self):
    #    assert isinstance(jfs.fs, JFS # TODO: FIX THIS

    def test_properties(self):
        assert isinstance(jfs.locked, bool)
        assert isinstance(jfs.read_locked, bool)
        assert isinstance(jfs.write_locked, bool)
        assert isinstance(jfs.capacity, int)
        assert isinstance(jfs.usage, int)
        #assert jfs.devices #TODO: test for generator of JFSDEvices

