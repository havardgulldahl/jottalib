#!/bin/bash

# test jotta cli tools

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
# Copyright 2016 Håvard Gulldahl <havard@gulldahl.no>


TMPDIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'mytmpdir');
STAMP=$(date +%s);
TESTFILE="$TMPDIR/Jotta/Archive/test/jottafuse.clitest.${STAMP}.txt";
INDIR=$(dirname "$TESTFILE");
TESTDIR="$INDIR/test-${STAMP}";
LOCALTESTFILE="${TMPDIR}/cli-${STAMP}-æøåöä.txt";
cat << HERE > "$LOCALTESTFILE"
Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec qu
HERE

BACK="$PWD";
cd "/tmp";

function cleanup {
  #mount | grep -q JottaCloudFS && unmount "$TMPDIR";
  cd "$BACK";
  rmdir "$TMPDIR";
}

function err {
  echo "$(tput setaf 1)ERROR: $*$(tput sgr0)";
  cleanup;
  exit 1;
}

function warn {
  echo "$(tput setaf 6)WARNING: $*$(tput sgr0)";

}

function info {
  echo "$(tput setaf 4)$*$(tput sgr0)";

}

info "Testing jottalib cli tools";

info "T1. Upload";
PYTHONPATH=src python -c 'from jottalib import cli; cli.upload()' "$LOCALTESTFILE" || err "upload() failed";
sleep 1;

info "T2. Download";

LOCALNAME=$(basename "$LOCALTESTFILE");
PYTHONPATH=src python -c 'from jottalib import cli; cli.download()' "$LOCALNAME" || err "download() failed";
diff -q "$LOCALTESTFILE" "$LOCALNAME" || err "download()ed file contents is not the same as orignal!";
sleep 1;

info "T3. Listing"

echo "$(tput setaf 3)Finishied$(tput sgr0)";
JDIR=$(dirname "$TESTFILE");
PYTHONPATH=src python -c 'from jottalib import cli; cli.ls()' "$JDIR" || err "ls() failed";
sleep 1;

cleanup;

#TODO
# def fuse(argv=None):
# def share(argv=None):
# def mkdir(argv=None):
# def rm(argv=None):
# def restore(argv=None):
# def cat(argv=None):
# def scanner(argv=None):
# def monitor(argv=None):
