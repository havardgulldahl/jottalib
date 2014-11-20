# encoding: utf-8
#
# This file is part of jottabox.
#
# jottabox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# jottabox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with jottabox.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014 Håvard Gulldahl <havard@gulldahl.no>

def compare(localtopdir, jottamountpoint):
    """Get a tree of local files and folders and compare it with what's currently on JottaCloud.

    For each folder, yields three set()s:
        onlylocal[] # files that only exist locally, i.e. newly added files that don't exist online,
        onlyremote[] # files that only exist in the JottaCloud, i.e. deleted locally
        bothplaces[] # files that exist both locally and remotely
    """

def new(localfile, jottapath):
    """Upload a new file from local disk (doesn't exist on JottaCloud).

    Returns JottaFile object"""


def replace_if_changed(localfile, jottapath):
    """Compare md5 hash to determine if contents have changed.
    Upload a file from local disk and replace file on JottaCloud if the md5s differ.

    Returns the JottaFile object"""


def delete(jottapath):
    """Remove file from JottaCloud because it is no longer present on local disk.
    Returns boolean"""
