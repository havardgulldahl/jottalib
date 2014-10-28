# JOTTALIB #

This is not an official Jottacloud client. It is developed [according to the company founder's instructions](http://forum.jotta.no/jotta/topics/api_http), with write support reverse engineered [with the company's blessing](http://forum.jotta.no/jotta/topics/jotta_api_for_remote_storage_fetch?).

## So what is it, then?

This is a bare-bones, pythonic interface to the Jottacloud backup/cloud storage service. The service itself exposes a nice and simple HTTP REST api, and this library wraps that interface in a python module, in the hope that it may be useful.

All code is GPLv3 licensed, and the [documentation lives at the official git repository](https://gitorious.org/jottafs/pages/Home). 

There is also a FUSE implementation in here, mostly to test the library, but it is fully working and ready for use as a file system.

## Caveats ##

Write support is reverse engineered and not based on official docs. Bugs patrol these waters! (Add them to the [bug tracker!](https://github.com/havardgulldahl/jottalib/issues/) )

## Requirements ##

The mandatory modules are listed in requirements.txt (`pip -r requirements.txt` will get you everything you need).

### Optional requirements ###

fusepy for Fuse client
python-qt4 for the Qt models

## How to get started ##

Export your Jottacloud username and password to the running environment. Running macosx or linux, it would normally go like this:

    `export JOTTACLOUD_USERNAME="yourusername"`
    `export JOTTACLOUD_PASSWORD="yourpassword"`

## Fuse client ##

This will "mount" jottacloud as a folder on your system, allowing you to use your normal file system utilities to browse your account.

1. Create a folder where you want your Jottacloud file system: 

       `mkdir $HOME/jottafs`

2. Run Fuse: 

       `jottafuse.py $HOME/jottafs`

Note. Being a remote mounted folder, it won't be as snappy as a locally synchronised folder like the official JottaCloud client. 


## QT models ## 

Take a look at qt.py, where you'll find a JFSModel(QtGui.QStandardItemModel) and various JFSNode(QtGui.QStandardItem) to match the jottacloud api.


## QT Gui

A simple try at a usable gui lives [in its own repository](https://gitorious.org/jottafs/jottagui).


