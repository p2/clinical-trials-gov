#!/bin/bash

# set UMLS credentials (from our external file!)
DIR=`dirname $0`
if [ ! -e "$DIR/umls.sh" ]; then
	echo The file "umls.sh" does not exist, create it with the two variables UMLS_USERNAME and UMLS_PASSWORD
	exit 1
fi

source $DIR/umls.sh

# set the run directory
RUN='.'
if [ -d $1 ]; then
	RUN=$1
fi

# cd into ctakes
if [ ! -d ctakes ]; then
	echo The "ctakes" directory is missing
	exit 1
fi

cd ctakes

# set maven options (give enough RAM!)
export MAVEN_OPTS="-Xmx2048M -Dctakes.umlsuser=$UMLS_USERNAME -Dctakes.umlspw=$UMLS_PASSWORD"

# execute!
mvn compile -X -PpgpopPreprocessAndSerialize -Dexec.args="-t ../$RUN/ctakes_input -l ../ctakes_label.txt -o ../$RUN/ctakes_output"

