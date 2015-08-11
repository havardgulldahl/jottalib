#!/bin/bash

function err {

	echo "ERROR: $*";
	exit 1;
}

source bin/activate || err "couldnt activate virtualenv";
VERSION=$(cat src/jottalib/__init__.py | cut -b14- | sed s/\'//) || err "couldnt get version";

echo "RELEASE JOTTALIB AND JOTTACLOUDCLIENT VERSION $VERSION:"
echo "=======================";
printf "Uploading cheese to pypi";
printf "... jottacloudclient";
ln -sf setup-jottacloudclient.py setup.py;
python setup.py sdist upload || err "jottacloudclient setup.py upload failed";
printf "... jottalib ";
ln -sf setup-jottalib.py setup.py;
python setup.py sdist upload || err "jottalib setup.py upload failed";
echo "=======================";
echo "Creating git tag $VERSION and pushing it to git server";
git tag -a "v$VERSION" -m "Version $VERSION release" || err "couldnt tag git tree";
git push --tags || err "problems pushing tags to central repository";
echo "=======================";
echo "Creating docs with pdoc";
(cd src; pdoc --overwrite --html-dir ../dist/docs/"$VERSION"/ --html jottalib;) || err "pdoc generating docs failed";
echo "=======================";
echo "Uploading docs to pypi";
python setup.py upload_docs --upload-dir dist/docs/"$VERSION"/jottalib  || err "couldnt upload docs to pypi";
echo "=======================";
rm setup.py;
echo "Enjoy your fresh $VERSION release!"

