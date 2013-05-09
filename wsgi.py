#!/usr/bin/python
#
#

import os
import sys
import logging
import bottle
import json
from jinja2 import Template, Environment, PackageLoader
from datetime import date, datetime
import dateutil.parser

from ClinicalTrials.study import Study
from ClinicalTrials.runner import Runner


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
@app.get('/trials/<nct>')
def get_trial(nct):
	""" Returns one trial. """
	
	trial = Study(nct)
	trial.load()
	
	return trial.json()


@app.get('/trial_runs')
def find_trials():
	""" Initiates the chain to find trials for the given condition or search-
	term. Supply with parameters "cond" or "term", the prior taking precedence.
	
	This method forks off and prints the status to a file which can be read by
	calling /trials_status/<run-id>. "run-id" is returned from this call.
	"""
	
	# get the runner
	run_id = datetime.now().isoformat()
	runner = Runner.get(run_id)
	if runner is None:
		runner = Runner(run_id, "run-server")
		runner.in_background = True
	
	# configure
	cond = bottle.request.query.get('cond')
	if cond is not None:
		runner.condition = cond
	else:
		term = bottle.request.query.get('term')
		if term is None:
			bottle.abort(400, 'You need to specify "cond" or "term"')
		else:
			runner.term = term
	
	# launch and return id
	runner.run()
	
	return run_id


@app.get('/trial_runs/<run_id>/progress')
def trial_progress(run_id):
	""" Returns text status from the file corresponding to the given run-id, if
	its missing returns a 404. """
	
	runner = Runner.get(run_id)
	if runner is None:
		bottle.abort(404)
	
	return runner.status


@app.get('/trial_runs/<run_id>/results')
def trial_results(run_id):
	""" Returns the results from a given run-id.
	Currently ignores the run-id since we only support one query at the time
	for testing purposes. """
	
	runner = Runner.get(run_id)
	if runner is None:
		bottle.abort(404)
	
	if not runner.done:
		bottle.abort(400, "Trial results are not available")
	
	ncts = runner.get_ncts(False)
	return json.dumps(ncts)

@app.get('/trial_runs/<run_id>/filter/<filter_by>')
def trial_filter_demo(run_id, filter_by):
	runner = Runner.get(run_id)
	if runner is None:
		bottle.abort(404)
	
	if not runner.done:
		bottle.abort(400, "Trial results are not available")
	
	# demographics - get age and gender
	if 'demographics' == filter_by:
		demo = demographics()
		is_male = "male" == demo.get('foaf:gender')
		bday_iso = demo.get('vcard:bday')
		bday = dateutil.parser.parse(bday_iso)		# no need for timezone correction
		age = dateutil.relativedelta.relativedelta(date.today(), bday).years
		
		ncts = runner.get_ncts(False)
		keep = []
		for nct in ncts:
			trial = Study(nct)
			trial.load()
			
			# filter gender
			if is_male:
				if trial.gender == 2:
					continue
			else:
				if trial.gender == 1:
					continue
			
			# filter age
			if trial.min_age > age or trial.max_age < age:
				continue
			
			keep.append(nct)
		
		runner.write_ncts(keep, True)
		return json.dumps(keep)
	
	# problems
	elif 'problems' == filter_by:
		probs = problems().get('problems', [])
		
		# extract snomed codes
		sno = []
		for problem in probs:
			snomed_url = problem.get('sp:problemName', {}).get('sp:code', {}).get('@id')
			if snomed_url is not None:
				snomed = os.path.basename(snomed_url)
				sno.append(snomed)
		
		# look at criteria
		ncts = runner.get_ncts(True)
		keep = []
		for nct in ncts:
			trial = Study(nct)
			trial.load()
			keep_this = True
			for crit in trial.criteria:
				
				# remove matching exclusion criteria
				if not crit.is_inclusion:
					intersection = set(sno).intersection(crit.snomed)
					if len(intersection) > 0:
						keep_this = False
						continue
			
			if keep_this:
				keep.append(nct)
		
		runner.write_ncts(keep, True)
		return json.dumps(keep)
	
	return '{"error": "We can not filter by %s"}' % filter_by


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
