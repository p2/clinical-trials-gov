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
	""" The index page """
	
	# render index
	template = _jinja_templates.get_template('index.html')
	return template.render(api_base='')


# ------------------------------------------------------------------------------ RESTful paths
@app.get('/demographics')
def demographics():
	""" Returns the current patient's demographics as JSON-LD.
	
	Currently just fake, reads from a static demographics file.
	"""
	
	d = {}
	with open('static/sample-demo.json') as handle:
		demo_ld = json.load(handle)
	
	for gr in demo_ld.get("@graph", []):
		if "sp:Demographics" == gr.get("@type"):
			d = gr
			break
	
	return d

@app.get('/problems')
def problems():
	""" Returns the current patient's problems as JSON-LD.
	
	Currently just fake, reads from a static problems file.
	"""
	
	problems = []
	with open('static/sample-problems.json') as handle:
		demo_ld = json.load(handle)
	
	# pick out the problems
	for gr in demo_ld.get("@graph", []):
		if "sp:Problem" == gr.get("@type"):
			problems.append(gr)
	
	return {'problems': problems}


# ------------------------------------------------------------------------------ Static Files
def _serve_static(file, root):
	""" Serves a static file or a 404 """
	try:
		return bottle.static_file(file, root=root)
	except Exception, e:
		bottle.abort(404)

@app.get('/static/<filename>')
def static(filename):
	return _serve_static(filename, 'static')

@app.get('/templates/<ejs_name>.ejs')
def ejs(ejs_name):
	return _serve_static('%s.ejs' % ejs_name, 'templates')


# setup logging
if __name__ == '__main__':
	if DEBUG:
		logging.basicConfig(level=logging.DEBUG)
	else:
		logging.basicConfig(level=logging.WARNING)
