#!/usr/bin/python
#
#  Run a local server


import os
import wsgi
import logging


# start the server
if wsgi.DEBUG:
	logging.basicConfig(level=logging.DEBUG)
	wsgi.bottle.run(app=wsgi.app, host='0.0.0.0', port=8008, reloader=True)
else:
	logging.basicConfig(level=logging.WARNING)
	wsgi.bottle.run(app=wsgi.app, host='0.0.0.0', port=8008)
