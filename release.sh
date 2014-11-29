#!/bin/bash

function err {

	echo "ERROR: $*";
	exit 1;
}

source bin/activate || err "couldnt activate virtualenv";
VERSION=$(python setup.py --version) || err "couldnt get version";

echo "=======================";
echo "Uploading egg to pypi";
python setup.py sdist upload || err "setup.py upload failed";
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
echo "Enjoy your fresh $VERSION release!"

