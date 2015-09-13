#!/bin/bash

# test jottafuse

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


TMPDIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'mytmpdir');
STAMP=$(date +%s);
TESTFILE="$TMPDIR/Jotta/Archive/test/jottafuse.bashtest.${STAMP}.txt";
INDIR=$(dirname "$TESTFILE");
TESTDIR="$INDIR/test-${STAMP}";
cat << HERE > /tmp/testdata.txt
Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec qu
HERE

function unmount {
    if [ -x /bin/fusermount ]
    then {
        R=$(/bin/fusermount -u "$1");
    } elif [ -x /usr/sbin/diskutil ];
    then {
        R=$(/usr/sbin/diskutil unmount "$1");
    } else {
        R=$(/bin/umount "$1");
    }
    fi
    return $?;

}

function cleanup {
  mount | grep -q JottaCloudFS && unmount "$TMPDIR";
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

info "Testing jottafuse implementation";

info "T1. Mount";
python src/jottafuse.py "$TMPDIR" || err "mounting jotta failed!";
sleep 2;

info "T2. Copy file";
cp /tmp/testdata.txt "$TESTFILE" || warn "copy failed!";
sleep 1;

info "T3. Read file";
diff -q /tmp/testdata.txt "$TESTFILE" || warn "read failed!";
sleep 1;

info "T4. Rename file";
mv "$TESTFILE" "${TESTFILE}-x" || warn "rename failed";
sleep 1;

info "T5. Overwrite file";
cp /tmp/testdata.txt "${TESTFILE}-x" || warn "overwrite copy failed!";
sleep 1;

info "T6. Delete file";
rm "${TESTFILE}-x" || warn "rm failed";


info "T7. Make folder";
mkdir "$TESTDIR" || warn "mkdir failed";
sleep 1;

info "T8. Rename folder";
mv "$TESTDIR" "${TESTDIR}-x" || warn "rename folder failed";
sleep 1;

info "T9. Remove folder";
rmdir "${TESTDIR}-x" || warn "removing folder failed";

info "T10. Statfs.";
df "$TMPDIR" 1>/dev/null || warn "statfs fsailed";

info "T11. Symlink";
ln -s /tmp/testdata.txt "${TESTFILE}-link" || warn "symlink failed";
sleep 1;
rm "${TESTFILE}-link" || warn "rm failed";

info "T12. Unmount";
unmount "$TMPDIR" || warn "unmounting jottafuse failed!";

echo "$(tput setaf 3)Finishied$(tput sgr0)";

cleanup;

#TODO
# GETATTR test
# TRUNCATE test
# READDIR test
# CACHING tests
