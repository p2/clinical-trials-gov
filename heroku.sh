#!/bin/bash
#
#  Script to set Heroku environment variables


if [ -f env.sh ]; then
	. ./env.sh
fi

read -p "App id (empty for default): " app_id

heroku config:set --app=$app_id \
	DEBUG=$DEBUG \
	USE_SMART=$USE_SMART \
	USE_SMART_05=$USE_SMART_05 \
	USE_APP_ID=$USE_APP_ID \
	USE_NLP=$USE_NLP \
	GOOGLE_API_KEY=$GOOGLE_API_KEY
