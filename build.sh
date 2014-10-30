#!/bin/bash

function err {

	echo "ERROR: $*";
	exit 1;
}

pandoc --from=markdown --to=rst --output=README.txt README.md || err "Pandoc failed";
python setup.py sdist $1 || err "setup.py failed"
rm README.txt

