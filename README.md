# JOTTALIB #

This is not an official Jottacloud client. It is developed [according to the company founder's instructions](http://forum.jotta.no/jotta/topics/api_http), with write support reverse engineered [with the company's blessing](http://forum.jotta.no/jotta/topics/jotta_api_for_remote_storage_fetch#reply_14928642).

## So what is it, then?

This is a bare-bones, pythonic interface to the Jottacloud backup/cloud storage service. The service itself exposes a nice and simple HTTP REST api, and this library wraps that interface in a python module, in the hope that it may be useful.

All code is GPLv3 licensed, and the [documentation is online](https://pythonhosted.org/jottalib/). 

There is also some simple tools and a FUSE implementation in here, mostly to test the library, but it is fully working and ready for use as a file system.

## Caveats

This code has **alpha status**, it's **not production ready** and **don't trust it with your data**! It might not eat your cat, but it might mangle your cat photos!

Write support is reverse engineered and not based on official docs. Bugs patrol these waters! (Add them to the [bug tracker!](https://github.com/havardgulldahl/jottalib/issues/) )

## Requirements

### Via pip

The easiest way: `pip install jottalib`

### From a local git clone

`pip install -r requirements.txt`

### Optional requirements

    fusepy for Fuse client
	python-qt4 for the Qt models

## How to get started

Export your Jottacloud username and password to the running environment. Running macosx or linux, it would normally go like this:

    export JOTTACLOUD_USERNAME="yourusername"
    export JOTTACLOUD_PASSWORD="yourpassword"

## Fuse client

This will "mount" jottacloud as a folder on your system, allowing you to use your normal file system utilities to browse your account.

0. Install `fusepy`

       pip install fusepy

1. Create a folder where you want your Jottacloud file system: 

       mkdir $HOME/jottafs

2. Run Fuse: 

       jottafuse.py $HOME/jottafs

Note. Being a remote mounted folder, it won't be anywhere as snappy as a locally synchronised folder. Since everything has to go over the network, performance will suffer. 

## QT models

Take a look at qt.py, where you'll find a JFSModel(QtGui.QStandardItemModel) and various JFSNode(QtGui.QStandardItem) to match the jottacloud api. Remember to `pip install python-qt4`


## QT Gui

A simple try at a usable gui lives [in its own repository](https://gitorious.org/jottafs/jottagui).


## Other tools

	`jottashare.py` - A simple command line script to easily upload and share a file at a public, secret URI

	`duplicity-backend.py` - WORK IN PROGRESS A module for duplicity. Store your backups in the JottaCloud


## Made by

The library is written by havard@gulldahl.no, with crucial help from jkaberg.com in revealing the details of the protocol.

