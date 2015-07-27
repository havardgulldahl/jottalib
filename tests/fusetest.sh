#!/bin/bash

# test jottafuse


TMPDIR=`mktemp -d 2>/dev/null || mktemp -d -t 'mytmpdir'`;
TESTFILE="$TMPDIR/Jotta/Archive/test/jottafuse.bashtest.data";
dd if=/dev/urandom bs=1 count=32 2>/dev/null | base64 -w 0 | rev | cut -b 2- | rev > /tmp/testdata;


python src/jottafuse.py $TMPDIR;

cp -iv /tmp/testdata "$TESTFILE" || echo "copy failed!";

test /tmp/testdata = "$TESTFILE" || echo "comparison failed!";

rm -iv "$TESTFILE" || echo "rm failed";