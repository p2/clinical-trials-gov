#!/bin/bash

# allocate enough RAM and set UMLS credentials (from our external file!)
DIR=`dirname $0`
source $DIR/umls.sh

export MAVEN_OPTS="-Xmx1024M -Dctakes.umlsuser=$UMLS_USERNAME -Dctakes.umlspw=$UMLS_PASSWORD"

cd ctakes

# execute!
#mvn exec:java -X \
#-Dexec.mainClass="org.chboston.cnlp.i2b2.features.CuiFeatureExtractor" \
#-Dexec.args="--input-dir ../grabbed --label-file ../testLblfile.txt --output-dir ../output"

mvn compile -PrunPGPOP \
-Dexec.args="--textRoot ../ctakes_input --labelFile ../labelFile.txt --outputRoot ../ctakes_output"

