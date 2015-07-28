#!/bin/bash

# test jottafuse

TMPDIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'mytmpdir');
STAMP=$(date +%s);
TESTFILE="$TMPDIR/Jotta/Archive/test/jottafuse.bashtest.${STAMP}.txt";
cat << HERE > /tmp/testdata.txt
Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec qu
HERE


function cleanup {
  umount "$TMPDIR" 2>&1 1>/dev/null;
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
test /tmp/testdata.txt = "$TESTFILE" || warn "comparison failed!";
sleep 1;

info "T4. Overwrite file";
cp /tmp/testdata.txt "$TESTFILE" || warn "overwrite copy failed!";

info "T5. Delete file";
rm "$TESTFILE" || warn "rm failed";

info "T6. Unmount";
umount "$TMPDIR" || warn "unmounting jottafuse failed!";

echo "$(tput setaf 3)Finishied$(tput sgr0)";

cleanup;