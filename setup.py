#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of jottalib.
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
# Copyright 2014-2016 Håvard Gulldahl <havard@gulldahl.no>

from setuptools import setup

import os
import sys
import os.path
import re
#sys.path.insert(0, './src')

# get metadata (__version__, etc) from module magic
with open(os.path.join('src', 'jottalib', '__init__.py')) as f:
    metadata = dict(re.findall("__([a-z]+)__\s*=\s*'([^']+)'", f.read()))

try:
    with open('README.txt') as f:
        long_desc = f.read()
except:
    long_desc = ''

REQUIRES = ['requests',
            'requests_toolbelt',
            'certifi',
            'clint',
            'python-dateutil',
            'humanize',
            'six',
            'chardet',]

# see https://pythonhosted.org/setuptools/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies
EXTRAS = {
          'Qt':  [],                 # required for qt models
          'FUSE':  [],               # required for jotta-fuse
          'monitor': ['watchdog',],  # required for jotta-monitor
          'scanner': [],             # optional for jotta-scanner
        }

if sys.platform != 'win32':
    # all the stuff that doesnt work on windows
    REQUIRES.append('lxml') 
    EXTRAS['scanner'].append('xattr')
    EXTRAS['FUSE'].append('fusepy')
    EXTRAS['Qt'].append('python-qt4')
else:
    print('WARNING: jottalib requires `lxml`, please get it from http://www.lfd.uci.edu/~gohlke/pythonlibs/')


setup(name='jottalib',
      version=metadata['version'],
      license='GPLv3',
      description='A library and tools to access the JottaCloud API',
      long_description=long_desc,
      author=u'Håvard Gulldahl',
      author_email='havard@gulldahl.no',
      url='https://github.com/havardgulldahl/jottalib',
      package_dir={'':'src'},
      packages=['jottalib', 'jottalib.contrib'],
      install_requires=REQUIRES,
      extras_require=EXTRAS,
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
              'jotta-scanner = jottalib.cli:scanner',
              'jotta-monitor = jottalib.cli:monitor',
              'jotta-cat = jottalib.cli:cat',
        ]
      },
      classifiers="""Intended Audience :: Developers
Intended Audience :: End Users/Desktop
License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)
Operating System :: OS Independent
Operating System :: Microsoft :: Windows
Operating System :: POSIX
Operating System :: POSIX :: Linux
Operating System :: MacOS :: MacOS X
Programming Language :: Python :: 2.7
Programming Language :: Python :: Implementation :: CPython
Programming Language :: Python :: Implementation :: PyPy
Topic :: System :: Archiving
Topic :: System :: Archiving :: Backup
Topic :: Utilities""".split('\n'),
     )
