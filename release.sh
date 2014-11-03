#!/bin/bash

function err {

	echo "ERROR: $*";
	exit 1;
}

source bin/activate || err "couldnt activate virtualenv";
VERSION=$(python setup.py --version) || err "couldnt get version";
python setup.py sdist upload || err "setup.py upload failed";
git tag -a "$VERSION" -m "Version $VERSION release" || err "couldnt tag git tree";
git push --tags || err "problems pushing tags to central repository";
pdoc --overwrite --html-dir dist/docs/"$VERSION" --html src/jottalib || err "pdoc generating docs failed";
python setup.py upload_docs --upload-dir dist/docs/"$VERSION"/jottalib  || err "couldnt upload docs to pypi";

echo "Enjoy your fresh $VERSION release!"
