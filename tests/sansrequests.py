# -*- encoding: utf-8 -*-
'Speed test jottalib without requests, only urllib3'
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
__version__ = '0.2.10a'

# import standardlib
import os, os.path, tempfile, time, math

import urllib3, certifi
urllib3.disable_warnings() # TODO FIX THIS

def humanizeFileSize(size):
    size = abs(size)
    if (size==0):
        return "0B"
    units = ['B','KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB']
    p = math.floor(math.log(size, 2)/10)
    return "%.3f%s" % (size/math.pow(1024,p),units[int(p)])

class JFS(object):
    def __init__(self, username, password):
        self.apiversion = '2.2' # hard coded per october 2014
        self.session = urllib3.connectionpool.connection_from_url('https://up.jottacloud.com',
                                                                  cert_reqs='CERT_REQUIRED',
                                                                  ca_certs=certifi.where())
        self.username = username
        self.headers = urllib3.util.make_headers(basic_auth='%s:%s' % (username, password))
        self.headers.update({'User-Agent':'jottalib %s (https://github.com/havardgulldahl/jottalib)' % (__version__, ),
                             'X-JottaAPIVersion': self.apiversion,
                            })
    def get(self, path):
        r = self.session.request('GET', '/jfs/%s%s' % (self.username, path), headers=self.headers)
        return r
