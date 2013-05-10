#!/usr/bin/python
#
#

import os
import sys
import logging
import json
import re
from datetime import date, datetime
import dateutil.parser

# bottle
import bottle
from beaker.middleware import SessionMiddleware
from jinja2 import Template, Environment, PackageLoader

# SMART
# from smart_client_python.smart import SmartClient
from rdflib.graph import Graph

# App
from ClinicalTrials.study import Study
from ClinicalTrials.runner import Runner


# bottle, beaker and Jinja setup
session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 300,
    'session.data_dir': './session_data',
    'session.auto': True
}
app = application = SessionMiddleware(bottle.app(), session_opts)		# "application" is needed for some services like AppFog
_jinja_templates = Environment(loader=PackageLoader('wsgi', 'templates'), trim_blocks=True)

DEBUG = True


# ------------------------------------------------------------------------------ Utilities
def _get_session():
	return bottle.request.environ.get('beaker.session')


# doesn't work with v0.5 and i2b2, leave in for v0.6 resurrection
# def _get_smart():
# 	sess = _get_session()
# 	if sess is None:
# 		return None
	
# 	# configure SMART client
# 	app_id = "clinical-trials-v05@apps.smartplatforms.org"
# 	server = {"api_base" : sess.get('api_base')}
# 	token = {
# 		"consumer_key": sess.get('rest_token'),
# 		"consumer_secret": sess.get('rest_secret')
# 	}
	
# 	smart = SmartClient(app_id, server, token)
# 	smart.record_id = sess.get('record_id')
	
# 	return smart


# ------------------------------------------------------------------------------ Index
@bottle.get('/')
@bottle.get('/index.html')
def index():
	""" The index page """
	
	# render index
	template = _jinja_templates.get_template('index.html')
	return template.render(api_base='')


# ------------------------------------------------------------------------------ RESTful paths
@bottle.put('/session')
def session():
	""" To change the current session parameters.
	PUT form-encoded requests here to update the client's session params.
	"""
	
	put_data = bottle.request.forms
	keys = put_data.keys()
	if keys is not None and len(keys) > 0:
		sess = _get_session()
		for key in keys:
			sess[key] = put_data[key]
		
		sess.save()
	
	return 'ok'


@bottle.get('/demographics')
def demographics():
	""" Returns the current patient's demographics as JSON extracted from JSON-LD.
	"""
	
	sess = _get_session()
	demo_rdf = sess.get('demographics') if sess is not None else None
	demo_ld = None
	d = {}
	
	# fallback to hardcoded data
	if demo_rdf is None:
		with open('static/sample-demo.json') as handle:
			demo_ld = json.load(handle)
	
	# use session data (parse RDF, convert to json-ld-serialization, load json... :P)
	else:
		try:
			# hack v0.5 format to be similar to v0.6 format, part 1
			demo_rdf = demo_rdf.replace('xmlns:v=', 'xmlns:vcard=')
			demo_rdf = demo_rdf.replace('<v:', '<vcard:')
			demo_rdf = demo_rdf.replace('</v:', '</vcard:')
			graph = Graph().parse(data=demo_rdf)
		except Exception, e:
			logging.error("Failed to parse demographics: %s" % e)
			return d
		
		# hack v0.5 format to be similar to v0.6 format, part 2
		demo_ld = {u"@graph": [json.loads(graph.serialize(format='json-ld'))]}
	
	# extract interesting pieces
	for gr in demo_ld.get("@graph", []):
		if "sp:Demographics" == gr.get("@type"):
			d = gr
			break
	
	return d


@bottle.get('/problems')
def problems():
	""" Returns the current patient's problems as JSON extracted from JSON-LD.
	"""
	
	sess = _get_session()
	prob_rdf = sess.get('problems') if sess is not None else None
	prob_ld = None

	# fallback to hardcoded data
	if prob_rdf is None:
		with open('static/sample-problems.json') as handle:
			prob_ld = json.load(handle)
	
	# use session data (parse RDF, convert to json-ld-serialization, load json... :P)
	else:
		try:
			graph = Graph().parse(data=prob_rdf)
		except Exception, e:
			logging.error("Failed to parse problems: %s\n%s" % (e, prob_rdf))
			return {'problems': []}
		
		prob_ld = json.loads(graph.serialize(format='json-ld'))
	
	# pick out the individual problems
	problems = []
	for gr in prob_ld.get("@graph", []):
		if "sp:Problem" == gr.get("@type"):
			problems.append(gr)
	
	return {'problems': problems}


# ------------------------------------------------------------------------------ Trials
@bottle.get('/trials/<nct>')
def get_trial(nct):
	""" Returns one trial. """
	
	trial = Study(nct)
	trial.load()
	
	return trial.json()


@bottle.get('/trial_runs')
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
		cond = re.sub(r'\s+\((disorder|finding)\)', '', cond)
		runner.condition = cond
	else:
		term = bottle.request.query.get('term')
		if term is None:
			bottle.abort(400, 'You need to specify "cond" or "term"')
		else:
			term = re.sub(r'\s+\((disorder|finding)\)', '', term)
			runner.term = term
	
	# launch and return id
	runner.run()
	
	return run_id


@bottle.get('/trial_runs/<run_id>/progress')
def trial_progress(run_id):
	""" Returns text status from the file corresponding to the given run-id, if
	its missing returns a 404. """
	
	runner = Runner.get(run_id)
	if runner is None:
		bottle.abort(404)
	
	return runner.status


@bottle.get('/trial_runs/<run_id>/results')
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


@bottle.get('/trial_runs/<run_id>/filter/<filter_by>')
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

@bottle.get('/static/<filename>')
def static(filename):
	return _serve_static(filename, 'static')

@bottle.get('/templates/<ejs_name>.ejs')
def ejs(ejs_name):
	return _serve_static('%s.ejs' % ejs_name, 'templates')


# setup logging
if __name__ == '__main__':
	if DEBUG:
		logging.basicConfig(level=logging.DEBUG)
	else:
		logging.basicConfig(level=logging.WARNING)
