# -*- encoding: utf-8 -*-
'Speed test jottalib'
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
import os, os.path, tempfile, time, math, logging
logging.captureWarnings(True)


from clint.textui import progress, puts, colored
from clint.textui.progress import Bar as ProgressBar

#import httplib
#httplib.HTTPConnection.debuglevel = 1



# import jotta
from jottalib import JFS, __version__
from sansrequests import JFS as LiteJFS

def humanizeFileSize(size):
    size = abs(size)
    if (size==0):
        return "0B"
    units = ['B','KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB']
    p = math.floor(math.log(size, 2)/10)
    return "%.3f%s" % (size/math.pow(1024,p),units[int(p)])

if __name__ == '__main__':
    # we need an active login to test
    import netrc
    try:
        n = netrc.netrc()
        username, account, password = n.authenticators('jottacloud.com') # read .netrc entry for 'machine jottacloud'
    except Exception as e:
        log.exception(e)
        username = os.environ['JOTTACLOUD_USERNAME']
        password = os.environ['JOTTACLOUD_PASSWORD']

    jfs = JFS.JFS(auth=(username, password))
    lite = LiteJFS(username, password)

    filesize = 1024*10*10

    data = os.urandom(filesize)
    testfile = tempfile.NamedTemporaryFile()
    puts(colored.blue('Creating test file.'))
    for i in progress.bar(range(0, 1000)):
        testfile.write(data)
    filesize = os.path.getsize(testfile.name)

    p = '/Jotta/Archive/test/%s.data' % os.path.basename(testfile.name)

    # UPLOAD TEST
    puts(colored.green('Test 1 | requests | Upload | File size: %s' % humanizeFileSize(filesize)))
    _start = time.time()
    progr = ProgressBar(expected_size=filesize)
    def UP(monitor, total):
        progr.show(monitor.bytes_read)
    fileobj = jfs.up(p, testfile, upload_callback=UP)
    _end = time.time()
    puts(colored.magenta("Network upload speed %s/sec \n" % ( humanizeFileSize( (filesize / (_end-_start)) ) )))

    # DOWNLOAD TEST 1
    puts(colored.green('Test 2 | requests | Read | File size: %s' % humanizeFileSize(filesize)))
    _start = time.time()
    x = fileobj.read()
    _end = time.time()
    puts(colored.magenta("Network download speed %s/sec \n" % ( humanizeFileSize( (filesize / (_end-_start)) ) )))
    del x

    # DOWNLOAD TEST 2
    puts(colored.green('Test 2 | requests | Stream | File size: %s' % humanizeFileSize(filesize)))
    progr2 = ProgressBar(expected_size=filesize)
    _start = time.time()
    _bytesread = 0
    for chunk in fileobj.stream():
        _bytesread = _bytesread + len(chunk)
        progr2.show(_bytesread)
    _end = time.time()
    puts(colored.magenta("Network download speed %s/sec \n" % ( humanizeFileSize( (filesize / (_end-_start)) ) )))

    # TODO: PRINT STATS IN A TABLE FOR COMPARISON / BOOKKEEPING
    # Versions: jottalib, urllib3, requests, jottaAPI
    # Server version from jottacloud.com

    # TEST WITHOUR REQUESTS, ONLY urllib3
    # UPLOAD TEST
    #
    # 2015-07-30 Disabled until urllib3 supports streaming uploads. HG
    #
    #
    #puts(colored.green('Test4. urllib3 upload speed. File size: %s' % humanizeFileSize(filesize)))
    #_start = time.time()
    #progr = ProgressBar(expected_size=filesize)
    #def UP(monitor, total):
    #    progr.show(monitor.bytes_read)
    #fileobj = lite.up(p, testfile)#, upload_callback=UP)
    #_end = time.time()
    #puts(colored.magenta("Network upload speed %s/sec" % ( humanizeFileSize( (filesize / (_end-_start)) ) )))

    # DOWNLOAD TEST 1
    puts(colored.green('Test 3 | urllib3 | Read | File size: %s' % humanizeFileSize(filesize)))
    _start = time.time()
    x = lite.get('%s?mode=bin' % p).read()
    _end = time.time()
    puts(colored.magenta("Network download speed %s/sec \n" % ( humanizeFileSize( (filesize / (_end-_start)) ) )))
    del x

    # DOWNLOAD TEST 2
    puts(colored.green('Test 3 | urllib3 | Stream | File size: %s' % humanizeFileSize(filesize)))
    progr2 = ProgressBar(expected_size=filesize)
    _start = time.time()
    _bytesread = 0
    for chunk in lite.get('%s?mode=bin' % p).stream():
        _bytesread = _bytesread + len(chunk)
        progr2.show(_bytesread)
    _end = time.time()
    puts(colored.magenta("Network download speed %s/sec" % ( humanizeFileSize( (filesize / (_end-_start)) ) )))

    # CLEANUP JOTTALIB
    fileobj.delete()

    #
    puts(colored.blue('\nFinished.'))
