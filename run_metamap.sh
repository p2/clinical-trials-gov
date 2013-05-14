#!/bin/bash

METAMAP=./bin/metamap12

# set the run directory
RUN='.'
if [ -d $1 ]; then
	RUN=$1
fi

# check for input files
if [ ! -d "$RUN/metamap_input" ]; then
	echo "There is no directory \"metamap_input\" in the run directory \"$RUN\""
	exit 1
fi
if [ ! -d "$RUN/metamap_output" ]; then
	mkdir "$RUN/metamap_output"
fi

# check for metamap
if [ ! -d metamap ]; then
	echo "The \"metamap\" directory is missing"
	exit 1
fi

cd metamap

# start servers if they are not running
if [ $(ps -ax | grep WSD_Server | wc -l) -lt 2 ]; then
	./bin/wsdserverctl start
	if [ 0 -ne $? ]; then
		echo "Failed to start WSD Server"
	fi
fi
if [ $(ps -ax | grep MedPost-SKR | wc -l) -lt 2 ]; then
	./bin/skrmedpostctl start
	if [ 0 -ne $? ]; then
		echo "Failed to start SKR"
	fi
fi

# run it
for f in "../$RUN/metamap_input/"*; do
	out=$(echo $f | sed s/_input/_output/)
	# $METAMAP --XMLf "$f" "$out"		# this shit does not work!!!
	# the only way it works is by piping echo!!! WHO DOES THIS???
	echo $(cat "$f") | $METAMAP --XMLf --silent | awk "NR>1" >"$out"
done

exit 0
