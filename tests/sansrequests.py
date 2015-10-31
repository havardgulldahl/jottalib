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
import os, os.path, tempfile, time, math, logging, datetime, hashlib

import urllib3, certifi
urllib3.disable_warnings() # TODO FIX THIS

def humanizeFileSize(size):
    size = abs(size)
    if (size==0):
        return "0B"
    units = ['B','KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB']
    p = math.floor(math.log(size, 2)/10)
    return "%.3f%s" % (size/math.pow(1024,p),units[int(p)])


def calculate_hash(fileobject, size=2**16):
    fileobject.seek(0, 2)
    size = fileobject.tell()
    fileobject.seek(0)
    md5 = hashlib.md5()
    for data in iter(lambda: fileobject.read(size), b''):
        md5.update(data)
    fileobject.seek(0)
    return (size, md5.hexdigest())


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

    def up(self, path, fileobject):
        url = path.replace('www.jotta.no', 'up.jottacloud.com')

        # Calculate file md5 hash
        contentlen, md5hash = calculate_hash(fileobject)

        log.debug('posting content (len %s, hash %s) to url %s', contentlen, md5hash, url)
        now = datetime.datetime.now().isoformat()
        headers = {'JMd5':md5hash,
                   'JCreated': now,
                   'JModified': now,
                   'X-Jfs-DeviceName': 'Jotta',
                   'JSize': contentlen,
                   'jx_csid': '',
                   'jx_lisence': ''
                   }
        params = {'cphash':md5hash,}
        fileobject.seek(0) # rewind read index for requests.post
        fields = {'md5': ('', md5hash),
                  'modified': ('', now),
                  'created': ('', now),
                  'file': (os.path.basename(url), fileobject.read(), 'application/octet-stream')}
        # TODO TODO: don't do fileobject.read() in previous line
        # we want to have a chunked upload, read the file piece by  piece
        # not sure how urllib3 supports this ATM
        sessheaders = self.headers.copy()
        headers.update(sessheaders)
        request = self.session.request_encode_body('POST',
                                                   url,
                                                   fields,
                                                   headers)

        return request
