#!/bin/sh
#
#  create a UMLS SQLite database.
#

# our SQLite database does not exist
if [ ! -e umls.db ]; then
	if [ ! -d "$1" ]; then
		echo "Provide the path to the UMLS install directory as first argument when invoking this script. Download the latest version here: http://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html (should check which file is needed)"
		exit 1
	fi
	if [ ! -d "$1/META" ]; then
		echo "There is no directory named META in the install directory you provided. Download the latest version here: http://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html"
		exit 1
	fi
	
	# init the database for MRDEF
	sqlite3 umls.db "CREATE TABLE MRDEF (
		CUI varchar,
		AUI varchar,
		ATUI varchar,
		SATUI varchar,
		SAB varchar,
		DEF text,
		SUPPRESS varchar,
		CVF varchar
	)"
	
	# convert RRF files (strip last pipe and remove quote (") characters, those are giving SQLite troubles)
	if [ ! -e "$1/META/MRDEF.pipe" ]; then
		current=$(pwd)
		cd "$1/META"
		echo "-> Converting RRF files for SQLite"
		# for f in *.RRF; do
		f=MRDEF.RRF
		sed -e 's/.$//' -e 's/"//g' "$f" > "${f%RRF}pipe"
		# done
		cd $current
	fi
	
	# import tables
	for f in "$1/META/"*.pipe; do
		table=$(basename ${f%.pipe})
		echo "-> Importing $table"
		sqlite3 umls.db ".import '$f' '$table'"
	done
	
	# create indexes
	echo "-> Creating indexes"
	sqlite3 umls.db "CREATE INDEX X_CUI ON MRDEF (CUI);"
	sqlite3 umls.db "CREATE INDEX X_SAB ON MRDEF (SAB);"
fi

