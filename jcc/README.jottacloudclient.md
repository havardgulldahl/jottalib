#JOTTA CLOUD CLIENT#

A cli friendly sync client for [JottaCloud](http://jottacloud.com).

It will sync your directory tree with JottaCloud, just like the official client.

**Note. This a third-party, not an official client.**

## Is it safe? ##

Being based on a reverse engineering of the protocol, things may break in unexpected ways. *Don't rely on this as your sole backup* unless you manually verify that the data is correctly transferred. **The authors won't be held responsible for any data loss.**

## How to get it ##

Run

    pip install jottacloudclient


##How to use it##

Run `jottacloudclientscanner.py` at some interval:

    python jottacloudclientscanner.py <top dir of your local tree> <the mount point on jottacloud>


The *top dir* is just an existing directory on your system that you want to backup.


The *mount point* is a path on JottaCloud. It's put together from a combination of **an existing device name**, **an existing backupdir** and **a folder name** (that will be created if it doesn't exist). Like this: `/<devicename>/<backupdir>/<foldername>`

Example:

    python jottacloudclientscanner.py /mnt/pictures /mybox/backup/pictures

###How it works###

The basic operation on the JottaCloud servers is to *make file level backups*. Unlike data-level protocols like `rsync`, the JottaCloud protocol does not seem to support [delta encoding](http://en.wikipedia.org/wiki/Delta_encoding), so file syncing needs to happen by copying the full file content.

To determine if a file needs to be updated, **Jotta Cloud Client** will compare the [md5 hash](http://en.wikipedia.org/wiki/MD5) of the local file with the one that the JottaCloud server reports. If the hashes differ, the client will upload the file. This is akin to how the official JottaCloud client works.


## Setup ##

The program needs to know your password to JottaCloud. There are two ways to do this.

### .netrc ###

Create a `$HOME/.netrc` file with this entry:

    machine jottacloud
            login <yourusername>
            password <yourpassword>

Make sure noone else can see it: `chmod 0600 $HOME/.netrc`.

### environment variables ###

Add  `JOTTACLOUD_USERNAME` AND `JOTTACLOUD_PASSWORD` as variables in the running environment:

    export JOTTACLOUD_USERNAME=<username> JOTTACLOUD_PASSWORD=<password>

#But it's not finished!#
#But it's not very advanced!#
#Geez, you should've added *super bright idea* already!#

Want to help out? Read the HACKING.md document and get cracking!

Send pull requests to [the git tree](https://gitorious.org/jottafs/jottacloudclient/) or [start fleshing out details in a bug report](https://github.com/havardgulldahl/jottalib/issues/new).


