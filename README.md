# JOTTALIB #

This is a bare-bones, pythonic interface to the Jottacloud backup/cloud storage service. The service itself exposes a nice and simple HTTP REST api, and this library wraps that interface in a python module, in the hope that it may be useful.

This is a community project, not an official Jottacloud product. It is developed [according to the company founder's instructions](http://forum.jotta.no/jotta/topics/api_http), with write support reverse engineered [with the company's blessing](http://forum.jotta.no/jotta/topics/jotta_api_for_remote_storage_fetch#reply_14928642).

All code is GPLv3 licensed, and the [documentation is online](https://pythonhosted.org/jottalib/). 

There are also some general tools and a FUSE implementation in here, mostly to test the library, but it is fully working and ready for use as a file system.

## Caveats

This code has **alpha status**, it's **not production ready** and **don't trust it with your data**! It might not eat your cat, but it might mangle your cat photos!

Write support is reverse engineered and not based on official docs. Bugs patrol these waters! (When you find them, add to the [bug tracker!](https://github.com/havardgulldahl/jottalib/issues/) )

## Installation

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

2. Run fuse **as a normal user**: 

       jottafuse.py $HOME/jottafs

*Note* Being a remote mounted folder, it won't be anywhere as snappy as a locally synchronised folder. Since everything has to go over the network, the performance will probably make you sad. 

## QT models

Take a look at `jottalib.qt`, where you'll find a JFSModel(QtGui.QStandardItemModel) class and various JFSNode(QtGui.QStandardItem) classes to match the jottacloud api. Using these classes you'll hopefully be able to focus on the UI/UX and leave the plumbing to jottalib.

Remember to `pip install python-qt4`

### QT Gui

A simple try at a usable gui, using the qt models provided here, lives [in its own repository](https://gitorious.org/jottafs/jottagui).

Have a nice idea for a swooshingly fresh JottaCloud app? Feel free to include these models in your own, grand design! And submit pull requests or ask for a linkback.

## jottashare.py

A simple command line script to easily upload and share a file at a public, secret URI

Usage: 

	jottashare.py <some great file you need to share>

## Duplicity backend

**WORK IN PROGRESS** 

The goal is to integrate JottaCloud with [duplicity](http://duplicity.nongnu.org/). Then we can run automated backups and store them in the JottaCloud.

## Authors

The library is written by havard@gulldahl.no, with crucial help from jkaberg.com in revealing the details of the protocol.

If you have a suggestion or have some new functionality in place, [let us know and we'll include it](https://github.com/havardgulldahl/jottalib/issues/) 
