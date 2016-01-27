JOTTALIB
========

|Join the chat at https://gitter.im/havardgulldahl/jottalib|
|Requirements Status| |Build status master branch| |pypi version| |pypi downloads| |coverage|

This is a rich, pythonic interface to the Jottacloud backup/cloud
storage service. The service itself exposes a nice and simple HTTP REST
api, and this library wraps that interface in a python module, in the
hope that it may be useful.

This is a community project, not an official Jottacloud product. It is
developed `according to the company founder's
instructions <http://forum.jotta.no/jotta/topics/api_http>`__, with
write support reverse engineered `explicitly blessed by company
staff <http://forum.jotta.no/jotta/topics/jotta_api_for_remote_storage_fetch#reply_14928642>`__.

All code is GPLv3 licensed, and the `documentation is
online <https://pythonhosted.org/jottalib/>`__.

In addition to the general library, you'll also find different backup
tools, some different plugins as well as a FUSE implementation in here.

Caveats
-------

This code is **not production ready** and it might not eat your cat, but it
might mangle your cat photos!

Write support is reverse engineered and not based on official docs. Bugs
patrol these waters! (When you find them, add to the `bug
tracker! <https://github.com/havardgulldahl/jottalib/issues/>`__ )

Installation
------------

Note that we've separated the code into different variants:

-  If you are a normal user, wanting to backup your stuff: get
   ``jottalib[scanner] and jottalib[monitor]``
-  If you are a developer and want to add connectivity to JottaCloud.com
   to your project, get ``jottalib``

Via pip
~~~~~~~

The easiest way: ``pip install jottalib[scanner]`` or ``pip install jottalib[monitor]``.

Optional requirements
~~~~~~~~~~~~~~~~~~~~~

These are all the extra variants you would install if you need it:

-  ``pip install jottalib[FUSE]`` for a Fuse client (`read more
   about
   it <https://github.com/havardgulldahl/jottalib/wiki/Normal-use-cases#i-want-a-virtual-jottacloud-file-system>`__)
-  ``pip install jottalib[scanner]`` for a tool to scan through a whole file
   folder on your system (`read more about
   it <https://github.com/havardgulldahl/jottalib/wiki/Normal-use-cases#i-want-a-drop-folder-so-everything-i-put-there-is-stored-automatically>`__)
-  ``pip install jottalib[monitor]`` for a tool to continuously monitor a
   folder on your system (`read more about
   it <https://github.com/havardgulldahl/jottalib/wiki/Normal-use-cases#i-want-a-drop-folder-so-everything-i-put-there-is-stored-automatically>`__)
-  ``pip install jottalib[Qt]`` for developers wanting to use the Qt
   models (`help is on the
   way <https://github.com/havardgulldahl/jottalib/wiki/Developers#qt-models>`__)

Documentation
-------------

To help both end users and developers to get started, a lot of use cases
are `covered in the
wiki <https://github.com/havardgulldahl/jottalib/wiki>`__.

Authors
-------

The library was initiated by havard@gulldahl.no, but **a project like
this needs a lot of community love**. Luckily patches, suggestions and
comments are trickling in, take a look at `AUTHORS.md <AUTHORS.md>`__
for the full picture.

If you notice something wrong, need some new functionality or want to
participate, `let us know about
it! <https://github.com/havardgulldahl/jottalib/issues/>`__

We need coders, quality assurance and power users alike, so if you want
to lend a hand, don't hesitate to open a new issue. Your help will be
much appreciated!

If you want to chat about a bug or ask a general question, you'll find
the core contributors `in the gitter.im
room <https://gitter.im/havardgulldahl/jottalib>`__. Come and take a
look!

.. |Join the chat at https://gitter.im/havardgulldahl/jottalib| image:: https://badges.gitter.im/Join%20Chat.svg
   :target: https://gitter.im/havardgulldahl/jottalib?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
.. |Requirements Status| image:: https://requires.io/github/havardgulldahl/jottalib/requirements.svg?branch=master
   :target: https://requires.io/github/havardgulldahl/jottalib/requirements/?branch=master
.. |Build status master branch| image:: https://travis-ci.org/havardgulldahl/jottalib.svg?branch=master
   :target: https://travis-ci.org/havardgulldahl/jottalib
.. |pypi version| image:: https://img.shields.io/pypi/v/jottalib.svg?style=flat
    :target: https://pypi.python.org/pypi/jottalib/
    :alt: Latest PyPI version
.. |pypi downloads| image:: https://img.shields.io/pypi/dm/jottalib.svg?style=flat
    :target: https://pypi.python.org/pypi/jottalib/
    :alt: Number of PyPI downloads
.. |coverage| image:: https://img.shields.io/coveralls/havardgulldahl/jottalib/master.svg?style=flat
   :target: https://coveralls.io/r/havardgulldahl/mopidy_plex
   :alt: Test coverage
