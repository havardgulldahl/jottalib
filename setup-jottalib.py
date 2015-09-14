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
# Copyright 2014,2015 Håvard Gulldahl <havard@gulldahl.no>

from setuptools import setup

import os
import sys
sys.path.insert(0, './src')

from jottalib import __version__

try:
    os.system('pandoc --from=markdown --to=rst --output=README.txt README.md')
    with open('README.txt') as f:
        long_desc = f.read()
except:
    long_desc = ''

package_version = '1'

setup(name='jottalib',
      version='%s-%s' % (__version__, package_version),
      license='GPLv3',
      description='A library to access the JottaCloud API',
      long_description=long_desc,
      author=u'Håvard Gulldahl',
      author_email='havard@gulldahl.no',
      url='https://github.com/havardgulldahl/jottalib',
      package_dir={'':'src'},
      packages=['jottalib', ],
      install_requires=['requests',
                        'requests_toolbelt',
                        'certifi',
                        'clint',
                        'python-dateutil',
                        'humanize',
                        'lxml'],
      # see https://pythonhosted.org/setuptools/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies
      extras_require={
          'Qt':  ['python-qt4',],
      },
      entry_points={
          'console_scripts': [
              'jotta-download = jottalib.cli:download',
              'jotta-fuse = jottalib.cli:fuse',
              'jotta-ls = jottalib.cli:ls',
              'jotta-mkdir = jottalib.cli:mkdir',
              'jotta-restore = jottalib.cli:restore',
              'jotta-rm = jottalib.cli:rm',
              'jotta-share = jottalib.cli:share',
              'jotta-upload = jottalib.cli:upload',
        ]
      },
      classifiers="""
Intended Audience :: Developers
License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)
Operating System :: OS Independent
Programming Language :: Python :: 2.7
Programming Language :: Python :: Implementation :: CPython
Programming Language :: Python :: Implementation :: PyPy
Topic :: System :: Archiving
Topic :: System :: Archiving :: Backup
Topic :: Utilities
""".split('\n'),
     )
