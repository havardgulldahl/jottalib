#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# jottashare.py 
# This file is part of https://gitorious.org/jottafs.
# 
# jottafs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# jottafs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with jottafs.  If not, see <http://www.gnu.org/licenses/>.
# 
# Copyright 2014 Håvard Gulldahl <havard@gulldahl.no>

# metadata

__author__ = 'havard@gulldahl.no'
__version__ = '0.1'

# importing stdlib
import sys, os, os.path
import urllib, logging, datetime
import argparse # 2.7

# import jotta
import jottalib


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(description='Share a file on JottaCloud and get the URI.')
    parser.add_argument('<local file>', help='The local file that you want to share')
    args = parser.parse_args()
    logging.debug(args)



