#!/bin/bash
#
#  run WSGI

# source environment
if [ -f env.sh ]; then
	. ./env.sh
else
	echo 'You really should create the file "env.sh" by copying "environment.sh" and adjusting to your liking'
fi

# start the server
./wsgi.py
