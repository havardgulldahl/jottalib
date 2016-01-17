#
# Created by S W on Sun, 31 Oct 2004 (PSF License)
#
# https://code.activestate.com/recipes/325905-memoize-decorator-with-timeout/
#
# This simple decorator is different to other memoize decorators in that it will
# only cache results for a period of time. It also provides a simple method of cleaning
# the cache of old entries via the .collect method. This will help prevent excessive
# or needless memory consumption.
#
#
# #The code below demonstrates usage of the MWT decorator. Notice how the cache is
# #cleared of some entries after the MWT().collect() method is called.
#
# @MWT()
# def z(a,b):
#     return a + b
#
# @MWT(timeout=5)
# def x(a,b):
#     return a + b
#
# z(1,2)
# x(1,3)
#
#
# print MWT()._caches
# >>> {<function 'z'>: {(1, 2): (3, 1099276281.092)},<function 'x'> : {(1, 3): (4, 1099276281.092)}}
#
# time.sleep(3)
# MWT().collect()
# print MWT()._caches
#>>> {<function 'z'>: {},<function 'x'> : {(1, 3): (4, 1099276281.092)}}
#

import time
import logging

log = logging.getLogger(__name__)

class MWT(object):
    """Memoize With Timeout"""
    _caches = {}
    _timeouts = {}

    def __init__(self,timeout=2):
        self.timeout = timeout

    def collect(self):
        """Clear cache of results which have timed out"""
        for func in self._caches:
            cache = {}
            for key in self._caches[func]:
                if (time.time() - self._caches[func][key][1]) < self._timeouts[func]:
                    cache[key] = self._caches[func][key]
            self._caches[func] = cache

    def __call__(self, f):
        self.cache = self._caches[f] = {}
        self._timeouts[f] = self.timeout

        def func(*args, **kwargs):
            kw = kwargs.items()
            kw.sort()
            key = (args, tuple(kw))
            try:
                v = self.cache[key]
                log.debug("get object from cache: %s", key)
                if (time.time() - v[1]) > self.timeout:
                    raise KeyError
            except KeyError:
                log.debug("new object in cache: %s", key)
                v = self.cache[key] = f(*args,**kwargs),time.time()
            return v[0]
        func.func_name = f.func_name

        return func


#
#
# This stuff added by the jottalib project, under the same terms as above (PSF License)
#

class Memoize(MWT):
    '''A superset of MWT that adds the possibility to yank paths from cached results'''
    def yank_path(self, path):
        """Clear cache of results from a specific path"""
        for func in self._caches:
            cache = {}
            for key in self._caches[func].keys():
                log.debug("cache key %s for func %s", key, func)
                if path in key[0]:
                    log.debug("del cache key %s", key)
                    del self._caches[func][key]
