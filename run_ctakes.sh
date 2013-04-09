#!/bin/bash

# allocate enough RAM and set UMLS credentials (from our external file!)
DIR=`dirname $0`
if [ ! -e "$DIR/umls.sh" ]; then
	echo The file "umls.sh" does not exist, create it with the two variables UMLS_USERNAME and UMLS_PASSWORD
	exit 1
fi

source $DIR/umls.sh

# cd into ctakes
if [ ! -d ctakes ]; then
	echo The "ctakes" directory is missing
	exit 1
fi

cd ctakes

export MAVEN_OPTS="-Xmx1024M -Dctakes.umlsuser=$UMLS_USERNAME -Dctakes.umlspw=$UMLS_PASSWORD"

# execute!
#mvn exec:java -X \
#-Dexec.mainClass="org.chboston.cnlp.i2b2.features.CuiFeatureExtractor" \
#-Dexec.args="--input-dir ../grabbed --label-file ../testLblfile.txt --output-dir ../output"

mvn compile -PrunPGPOP \
-Dexec.args="--textRoot ../ctakes_input --labelFile ../labelFile.txt --outputRoot ../ctakes_output"

