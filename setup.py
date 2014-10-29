#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of jottafs.
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

from distutils.core import setup

import os, sys
sys.path.insert(0, './src')

from jottalib import JFS

os.system('''pandoc --from=markdown --to=rst --output=README.txt README.md''')

with open('README.txt') as f:
    long_desc = f.read()

setup(name='jottalib',
      version=JFS.__version__,
      license='GPLv3',
      description='A library to access the JottaCloud API',
      long_description=long_desc,
      author=u'Håvard Gulldahl',
      author_email='havard@gulldahl.no',
      url='https://gitorious.org/jottafs',
      package_dir={'':'src'},
      packages=['jottalib', ],
      scripts=['src/jottafuse.py', 'src/jottashare.py'],
      data_files=[ ('share', ['COPYING', 'README.api']), ]
     )

os.remove('README.txt')

