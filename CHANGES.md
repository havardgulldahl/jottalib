# Change Log

## [0.5] - TBA

## [0.4.2] - 2016-01-23

### Bug fixes

- Fix bug in installation script that left out `jottalib.contrib`.

## [0.4.1] - 2016-01-23

### Bug fixes

- Fix Unicode error in md5 hash routine, see #79. Thanks @malinkb for the reports.
- Don't fail if `xattr` is not installed 

### Changed

- jotta-scanner: The default behaviour is now to never delete remote files, unless explicitly told so
                 by way of one of the new flags `--prune-files`, `--prune-folders` or `--prune-all`
                 See discussion in https://github.com/havardgulldahl/jottalib/pull/80. By @cowai.

## [0.4] - 2016-01-21

### BREAKING CHANGES

- Some modules and scripts have been renamed. We realise this might cause inconvenience for some, but it has been long time coming.
    o `jottacloudclientscanner.py` and `jottacloudclientmonitor.py` are long gone. Their new names are `jotta-scanner` and `jottalib-monitor` once you install it.
    o Developers: The modules are also renamed: `jottalib.scanner` and `jottalib.monitor` are your new friends.

- `.netrc` parsing has changed. Update your entry to read **jottacloud.com**, instead of **jottacloud**


### Changed

- A lot of new tests added, and some small bugs caught and fixed.

### Bug fixes

- URLs are now properly escaped, see bug#25, by @cowai / Ari Selseng

### Added

- Consistent paths, by @mortenlj, see bug#39
- jotta-scanner can keep checksums in `xattr` file attributes, if supported. This speeds up things.
- New strategy to cache dir entries for `fuse`, see 3fe71b237db4ea45bedadc4784225c889cbf8e91
- A lot of cli tools by @thusoy/ Tarjei Husøy.
- Better logging messages by @forsberg  / Erik Forsberg
- Beginning of proper py3 support, by @ttyridal / Torbjørn Tyridal
- Methods to create mountpoints and devices, by @ttyridal
- Add support for exclude patterns, see #44 by @mortenlj


Thanks to all contributors!

## [0.3.1] - 2015-08-26

### Changed

- `jottacloudclientscanner.py` now supports excluding files and directory matching a regex. Thanks Morten Lied Johansen

### Fixed

- Fix regression in `jottafuse.py` on linux, where attempting to read data beyond file size would return an error instead of all the data there is. See bug#43




## [0.3] - 2015-08-12


### Security

- a28f93d4ec4fd03b0f669f580cb8a22dcdf5e319 This project now uses the `certifi` package to use system certificates for https
- d61a9bbdc17716ff9e40a7bd7eaa56f6737a4dc2 Stop pinning requests and requests_cache, it is dangerous


### Changed

- The project main repository is now on github
- 165a283d76695b5f197ece6581725c3874e09cfb Merge `jottalib` and `jottacloudclient` packages to accomplish the following
  - install jottafuse.py and jottashare.py with `jottacloudclient`, not `jottalib`
  - Add two *extras* to the `jottacloudclient` package, namely `[FUSE]` and `[monitor]`. Install it like this:

        pip install jottacloudclient[FUSE]

- Add a new script: `jottacloudclientmonitor.py`, that will monitor a folder for changes and upload immediately. *Tested on Windows, Linux and OSX*
- a89cc2c9cc0f89723cf85aff5c073c69f8fdaddd Add a new mode to `jottafuse.py`, the fastest way to upload local files is to **create a symlink** in your *FUSE* mounted folder.
- Added automatic testing, which will help us keep the code base more stable as work progresses
- 519292a1f9e942d2ead67b6a995fc55405e0b24e Added support for resuming uploads.
- 58c8b70dd7df1dc98d74a7e6629e32a3a0b79a77 `jottalib` Allow per-file progress to be measured during upload. **Contribution by @alexschrod**

### Fixed
- `jottafuse.py` is much, much, much faster now.
- 6cae757bd9ceefa347919f495a1426220dc19f45 Fix off-by-one byte error in `JFSFile.readpartial()`
- e37a63f5e8f6857c68f933e89c1b43e678436009 Bug fix: rewrite ternary conditionals as "X if Y else Z"
- 079b9f09f6962ab3c9cfd7d8ee36869a0c45a954 Catch odd cases where a device has no mount points. See bug #26
- d383697924eb65be85b5126d43e97a6a6e85655f Skip symlinks in `jottacloudclientmonitor.py` altogether. See bug #28
- d5a7cbd3df24c4e44124fdcd8b21b4221b65e67f `jottalib` now properly reads and uploads files that are larger than available memory. **Contribution by @alexschrod**

