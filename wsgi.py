#!/usr/bin/python
#
#

import os
import sys
import logging
import bottle
import json
from jinja2 import Template, Environment, PackageLoader
from datetime import datetime
from subprocess import call
from threading import Thread

from ClinicalTrials.study import Study
from ClinicalTrials.lillycoi import LillyCOI
from ClinicalTrials.umls import UMLS


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


# ------------------------------------------------------------------------------ Trials
@app.get('/trials')
def find_trials():
	""" Initiates the chain to find trials for the given condition or search-
	term. Supply with parameters "cond" or "term", the prior taking precedence.
	
	This method forks off and prints the status to a file which can be read by
	calling /trials_status/<run-id>. "run-id" is returned from this call.
	"""
	
	cond = bottle.request.query.get('cond')
	term = None
	if cond is None:
		term = bottle.request.query.get('term')
		if term is None:
			bottle.abort(400, 'You need to specify "cond" or "term"')
	
	run_id = datetime.now().isoformat()
	worker = Thread(target=run_trials, args=(run_id, cond, term))
	worker.start()
	
	return run_id


def run_trials(run_id, condition=None, term=None):
	""" Runs the whole toolchain -- MOVE TO FILE/CLASS.
	Currently writes all status to a file associated with run_id. If the first
	word in that file is "error", the process is assumed to have stopped.
	"""
	
	# prepare a run directory (for now it's always the same)
	run_dir = "run-server"
	if not os.path.exists(run_dir):
		os.mkdir(run_dir)
		os.mkdir(os.path.join(run_dir, 'ctakes_input'))
		os.mkdir(os.path.join(run_dir, 'ctakes_output'))
	
	# setup
	db_path = os.path.join(run_dir, 'storage.db')
	Study.setup_tables(db_path)
	Study.setup_ctakes({'root': run_dir, 'cleanup': False})
	UMLS.import_snomed_if_necessary()
	
	# search for studies
	with open(run_id, 'w') as handle:
		handle.write("Fetching %s studies..." % condition if condition is not None else term)
	
	lilly = LillyCOI()
	if condition is not None:
		results = lilly.search_for_condition(condition, True, ['id', 'eligibility'])
	else:
		results = lilly.search_for_term(term, True, ['id', 'eligibility'])
	
	# process all studies
	run_ctakes = False
	i = 0
	for study in results:
		i += 1
		with open(run_id, 'w') as handle:
			handle.write('Processing %d of %d...' % (i, len(results)))
		 
		study.load()
		study.process_eligibility_from_text()
		study.codify_eligibility()
		if study.waiting_for_ctakes():
			run_ctakes = True
		study.store()
	
	# run cTakes if needed
	if run_ctakes:
		with open(run_id, 'w') as handle:
			handle.write('Running cTakes (this will take a while)...')
		
		try:
			if call(['./run_ctakes.sh', run_dir]) > 0:
				with open(run_id, 'w') as handle:
					handle.write('Error running cTakes')
					return
		except Exception, e:
			with open(run_id, 'w') as handle:
				handle.write('Error running cTakes: %s' % e)
				return
		
		# make sure we got all criteria
		for study in results:
			study.codify_eligibility()
			study.store()
	
	Study.sqlite_commit_if_needed()
	os.remove(run_id)


@app.get('/trials/<run_id>/progress')
def trial_progress(run_id):
	""" Returns text status from the file corresponding to the given run-id, if
	its missing the run is assumed to have ended and "done" is returned. """
	
	status = 'done'
	
	if os.path.exists(run_id):
		with open(run_id) as handle:
			status = handle.read()
	
	return status

@app.get('/trials/<run_id>/results')
def trial_results(run_id):
	""" Returns the results from a given run-id.
	Currently ignores the run-id since we only support one query at the time
	for testing purposes. """
	
	return "Found some studies"



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
