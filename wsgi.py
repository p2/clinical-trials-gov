#!/usr/bin/python
#
#

import logging
import bottle
import json
from jinja2 import Template, Environment, PackageLoader


# bottle and Jinja setup
app = application = bottle.Bottle()			# "application" is needed for some services like AppFog

_jinja_templates = Environment(loader=PackageLoader('wsgi', 'templates'), trim_blocks=True)

DEBUG = True



# ------------------------------------------------------------------------------ Index
@app.get('/')
@app.get('/index.html')
def index():
	""" Serve the index page. """
	return "Hello World"


# setup logging
if __name__ == '__main__':
	if DEBUG:
		logging.basicConfig(level=logging.DEBUG)
	else:
		logging.basicConfig(level=logging.WARNING)
