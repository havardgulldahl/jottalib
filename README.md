# JOTTALIB #

[![Join the chat at https://gitter.im/havardgulldahl/jottalib](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/havardgulldahl/jottalib?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[![Requirements Status](https://requires.io/github/havardgulldahl/jottalib/requirements.svg?branch=master)](https://requires.io/github/havardgulldahl/jottalib/requirements/?branch=master)

This is a rich, pythonic interface to the Jottacloud backup/cloud storage service. The service itself exposes a nice and simple HTTP REST api, and this library wraps that interface in a python module, in the hope that it may be useful.

This is a community project, not an official Jottacloud product. It is developed [according to the company founder's instructions](http://forum.jotta.no/jotta/topics/api_http), with write support reverse engineered [explicitly blessed by company staff](http://forum.jotta.no/jotta/topics/jotta_api_for_remote_storage_fetch#reply_14928642).

All code is GPLv3 licensed, and the [documentation is online](https://pythonhosted.org/jottalib/).

In addition to the general library, you'll also find different backup tools, some different plugins as well as a FUSE implementation in here.

## Caveats

This code has **alpha status**, it's **not production ready** and **don't trust it with your data**! It might not eat your cat, but it might mangle your cat photos!

Write support is reverse engineered and not based on official docs. Bugs patrol these waters! (When you find them, add to the [bug tracker!](https://github.com/havardgulldahl/jottalib/issues/) )

## Installation

Note that we've separated the code into two packages:

 * If you are a normal user, wanting to backup your stuff: get `jottacloudclient`
 * If you are a developer and want to add connectivity to JottaCloud.com to your project, get
 `jottalib`


### Via pip

The easiest way: `pip install jottacloudclient` or `pip install jottalib`.


### Optional requirements


These are extras you would install if you need it:

  * `pip install jottacloudclient[FUSE]` for a Fuse client (see below)
  * `pip install jottacloudclient[monitor]` for a tool to contiually monitor a folder on your system (see below)
  * `pip install jottalib[Qt]` for developers wanting to use the Qt models

## How to get started

Export your Jottacloud username and password to the running environment. Running macosx or linux, it would normally go like this:

    export JOTTACLOUD_USERNAME="yourusername"
    export JOTTACLOUD_PASSWORD="yourpassword"

## Crontab client

The **main use case** for Jottacloud customers is probably a (headless) client that works the same way as the official clients. That is, a program that automatically mirrors every file in some paths and keeps a file-by-file copy up to date in the cloud.  That way you'll get a tried and tested, cross-platform backup solution.

Take a look at `jottacloudclientscanner.py` from `jottacloudclient`, which will scan through a local file tree and make sure the online tree is in sync. And when you get it up and running, add it to your `crontab` / `schtasks.exe` and enjoy some fresh air. Your files are safe! (But who knows about your cat photos)

## FUSE client, a.k.a. Virtual jottacloud file system

This will "mount" jottacloud as a folder on your system, allowing you to use your normal file system utilities to browse your account.

*Note* Being a remote mounted folder, it won't be anywhere as snappy as a locally synchronised folder. Since everything has to go over the network, and Jottacloud never intended for this kind of use, the **performance will probably make you sad**.

0. Install necessary stuff:

       `pip install jottacloudclient[FUSE]`

1. Create a folder where you want your Jottacloud file system:

       `mkdir $HOME/jottafs`

2. Run fuse **as a normal user**:

       `jottafuse.py $HOME/jottafs`


## QT models

Take a look at `jottalib.qt`, where you'll find a JFSModel(QtGui.QStandardItemModel) class and various JFSNode(QtGui.QStandardItem) classes to match the jottacloud api. Using these classes you'll hopefully be able to focus on the UI/UX and leave the plumbing to jottalib.

Remember to `pip install jottalib[Qt]` first.

## jottashare.py

A simple command line script to easily upload and share a file at a public, secret URI

Usage:

	jottashare.py <some great file you need to share>

## Duplicity backend

The goal is to integrate JottaCloud with [duplicity](http://duplicity.nongnu.org/). Then we can run automated backups and store them in the JottaCloud.

## Authors

The library was initiated by havard@gulldahl.no, but **a project like this needs a lot of community love**. Luckily patches, suggestions and comments are trickling in, take a look at [authors.md](authors.md) for the full picture.

If you notice something wrong, need some new functionality or want to participate, [let us know about it!](https://github.com/havardgulldahl/jottalib/issues/)

We need coders, quality assurance and power users alike, so if you want to lend a hand, don't hesitate to open a new issue. Your help will be much appreciated.
