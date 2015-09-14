#!/bin/bash
#
# Thank you, https://github.com/akiradeveloper/nim-fuse/blob/master/test/test_linux.sh


PROGNAME=$1

CURDIR="`pwd`"

cat > umltest.inner.sh <<EOF
#!/bin/sh
(
   set -e
   set -x
   insmod /usr/lib/uml/modules/\`uname -r\`/kernel/fs/fuse/fuse.ko
   cd "$CURDIR"
   ./$PROGNAME
   echo Success
)
echo "\$?" > "$CURDIR"/umltest.status
halt -f
EOF

chmod +x umltest.inner.sh

/usr/bin/linux.uml mem=256M init=`pwd`/umltest.inner.sh rootfstype=hostfs rw

exit $(<umltest.status)