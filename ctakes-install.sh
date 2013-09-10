#!/bin/bash
#
# Download and install cTAKES
#
# Dependencies:
# - java
# - mvn (Maven)
# - svn (Subversion)


# checkout ctakes from SVN
if [ ! -d ctakes-svn ]; then
	echo "->  Checking out cTAKES from Subversion repo"
	svn co https://svn.apache.org/repos/asf/ctakes/trunk ctakes-svn
else
	echo "->  Updating cTAKES repo"
	cd ctakes-svn
	svn up
	cd ..
fi

# package
echo "->  Packaging cTAKES"
cd ctakes-svn
mvn package

# extract and move built products into place
echo "->  Moving things into place"
base=$(echo ctakes-distribution/target/*-bin.tar.gz)
tar xzf $base
mv $(basename ${base%-bin.tar.gz}) ctakes

# add special classes
cd ..
cp ctakes-extras/* ctakes/
echo "->  Done"
