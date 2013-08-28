#!/bin/bash
#
#  run WSGI

# source environment
if [ -f env.sh ]; then
	. ./env.sh
fi

# start the server
./wsgi.py
