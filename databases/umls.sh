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
	
	# convert RRF files (strip last pipe and remove quote (") characters, those are giving SQLite troubles)
	if [ ! -e "$1/META/MRDEF.pipe" ]; then
		current=$(pwd)
		cd "$1/META"
		echo "-> Converting RRF files for SQLite"
		for f in MRCONSO.RRF MRDEF.RRF; do
			sed -e 's/.$//' -e 's/"//g' "$f" > "${f%RRF}pipe"
		done
		cd $current
	fi
	
	# init the database for MRDEF
	# table structure here: http://www.ncbi.nlm.nih.gov/books/NBK9685/
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
	
	# init the database for MRCONSO
	sqlite3 umls.db "CREATE TABLE MRCONSO (
		CUI varchar,
		LAT varchar,
		TS varchar,
		LUI varchar,
		STT varchar,
		SUI varchar,
		ISPREF varchar,
		AUI varchar,
		SAUI varchar,
		SCUI varchar,
		SDUI varchar,
		SAB varchar,
		TTY varchar,
		CODE varchar,
		STR text,
		SRL varchar,
		SUPPRESS varchar,
		CVF varchar
	)"
	
	# import tables
	for f in "$1/META/"*.pipe; do
		table=$(basename ${f%.pipe})
		echo "-> Importing $table"
		sqlite3 umls.db ".import '$f' '$table'"
	done
	
	# create faster lookup table
	sqlite3 umls.db "CREATE TABLE descriptions AS SELECT CUI, LAT, STR FROM MRCONSO WHERE LAT = 'ENG' AND TS = 'P' AND ISPREF = 'Y'"
	
	# create indexes
	echo "-> Creating indexes"
	sqlite3 umls.db "CREATE INDEX X_CUI_MRDEF ON MRDEF (CUI);"
	sqlite3 umls.db "CREATE INDEX X_SAB_MRDEF ON MRDEF (SAB);"
	sqlite3 umls.db "CREATE INDEX X_CUI_MRCONSO ON MRCONSO (CUI);"
	sqlite3 umls.db "CREATE INDEX X_LAT_MRCONSO ON MRCONSO (LAT);"
	sqlite3 umls.db "CREATE INDEX X_TS_MRCONSO ON MRCONSO (TS);"
	sqlite3 umls.db "CREATE INDEX X_CUI_desc ON descriptions (CUI);"
fi

