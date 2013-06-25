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
from settings import USE_APP_ID, USE_SMART_05, USE_NLP, DEBUG, ENDPOINTS
if not USE_SMART_05:
	from smart_client_python.client import SMARTClient
from rdflib.graph import Graph

# App
from ClinicalTrials.study import Study
from ClinicalTrials.runner import Runner
from ClinicalTrials.umls import SNOMEDLookup


# bottle, beaker and Jinja setup
session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 300,
    'session.data_dir': './session_data',
    'session.auto': True
}
app = application = SessionMiddleware(bottle.app(), session_opts)		# "application" is needed for some services like AppFog
_jinja_templates = Environment(loader=PackageLoader('wsgi', 'templates'), trim_blocks=True)



# ------------------------------------------------------------------------------ Utilities
def _get_session():
	return bottle.request.environ.get('beaker.session')		

# only used for SMART v0.6+
def _get_smart():
	sess = _get_session()
	if sess is None:
		logging.debug("There is no session")
		return None
	
	# configure SMART client
	api_base = sess.get('api_base')
	if not api_base:
		logging.debug("No api_base is set")
		return None
	
	# find server credentials
	cons_key = sess.get('rest_token')
	cons_sec = sess.get('rest_secret')
	if not cons_key or not cons_sec:
		server = None
		for ep in ENDPOINTS:
			if ep.get('url') == api_base:
				server = ep
				break
		
		if server is None:
			logging.error("There is no server with base URI %s" % api_base)
			return None
		
		cons_key = server.get('consumer_key')
		cons_sec = server.get('consumer_secret')
	
	# init client
	token = {
		'consumer_key': cons_key,
		'consumer_secret': cons_sec
	}
	
	try:
		smart = SMARTClient(USE_APP_ID, api_base, token)
		smart.record_id = sess.get('record_id')
	except Exception, e:
		logging.warning("Failed to instantiate SMART client: %s" % e)
		smart = None
	
	return smart


# ------------------------------------------------------------------------------ Index
@bottle.get('/')
@bottle.get('/index.html')
def index():
	""" The index page """
	sess = _get_session()
	
	# look at URL params first, if they are there store them in the session
	api_base = bottle.request.query.get('api_base')
	if api_base:
		sess['api_base'] = api_base
		
	else:
		api_base = sess.get('api_base')
	
	# determine record id
	record_id = bottle.request.query.get('record_id')
	if record_id is not None:
		if '0' != record_id:
			sess['record_id'] = record_id
		else:
			del sess['record_id']
			record_id = None
	else:
		record_id = sess.get('record_id')
	
	# no endpoint, show selector
	if not api_base:
		logging.debug('redirecting to endpoint selection')
		bottle.redirect('endpoint_select')
	
	smart = _get_smart()
	if smart is None:
		return "Cannot connect to SMART sandbox"
	
	# no record id, call launch page
	if record_id is None:
		launch = smart.launch_url
		if launch is None:
			return "Unknown app start URL, cannot launch without an app id"
		
		logging.debug('redirecting to app launch page')
		bottle.redirect(launch)
		return
	
	# render index
	template = _jinja_templates.get_template('index.html')
	return template.render(smart_v05=USE_SMART_05, has_chrome=False, api_base=api_base)


@bottle.get('/endpoint_select')
def endpoints():
	""" Shows all possible endpoints, sending the user back to index when one is chosen """
	
	# get the callback
	# NOTE: this is done very cheaply, we need to make sure to end the url with either "?" or "&"
	callback = bottle.request.query.get('callback', 'index.html?')
	if '?' != callback[-1] and '&' != callback[-1]:
		callback += '&' if '?' in callback else '?'
	
	available = []
	for srvr in ENDPOINTS:
		available.append(srvr)
	
	# render selections
	template = _jinja_templates.get_template('endpoint_select.html')
	return template.render(endpoints=available, callback=callback)
	

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
		if USE_NLP:
			runner.run_ctakes = True
			#runner.run_metamap = True
	
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
	runner.run(['id', 'acronym', 'brief_title', 'official_title', 'brief_summary', 'eligibility', 'location'])
	
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
	""" Returns the results from a given run-id. """
	
	runner = Runner.get(run_id)
	if runner is None:
		bottle.abort(404)
	
	if not runner.done:
		bottle.abort(400, "Trial results are not available")
	
	ncts = runner.get_ncts()
	return json.dumps(ncts)


@bottle.get('/trial_runs/<run_id>/filter/<filter_by>')
def trial_filter_demo(run_id, filter_by):
	runner = Runner.get(run_id)
	if runner is None:
		bottle.abort(404)
	
	if not runner.done:
		bottle.abort(400, "Trial results are not available")
	
	ncts = runner.get_ncts()
	
	# demographics - get age and gender
	if 'demographics' == filter_by:
		demo = demographics()
		is_male = "male" == demo.get('foaf:gender')
		bday_iso = demo.get('vcard:bday')
		bday = dateutil.parser.parse(bday_iso)		# no need for timezone correction
		age = dateutil.relativedelta.relativedelta(date.today(), bday).years
		
		keep = []
		for tpl in ncts:
			nct = tpl[0]
			reason = tpl[1] if len(tpl) > 1 else None
			
			if not reason:
				trial = Study(nct)
				trial.load()
				
				# filter gender
				if is_male:
					if trial.gender == 2:
						reason = "Limited to women"
				else:
					if trial.gender == 1:
						reason = "Limited to men"
				
				# filter age
				if trial.min_age > age:
					reason = "Patient is too young (min age %d)" % trial.min_age
				elif trial.max_age < age:
					reason = "Patient is too old (max age %d)" % trial.max_age
			
			if reason:
				keep.append((nct, reason))
			else:
				keep.append((nct,))
		
		runner.write_ncts(keep)
		ncts = keep
	
	# problems (only if NLP is on)
	elif 'problems' == filter_by:
		if USE_NLP:
			probs = problems().get('problems', [])
			
			# extract snomed codes from patient's problem list
			snomed = SNOMEDLookup()
			exclusion_codes = []
			for problem in probs:
				snomed_url = problem.get('sp:problemName', {}).get('sp:code', {}).get('@id')
				if snomed_url is not None:
					snomed_code = os.path.basename(snomed_url)
					exclusion_codes.append(snomed_code)
			
			# look at trial criteria
			keep = []
			for tpl in ncts:
				nct = tpl[0]
				reason = tpl[1] if len(tpl) > 1 else None
				
				if not reason:
					trial = Study(nct)
					trial.load()
					for crit in trial.criteria:
						
						# remove matching exclusion criteria
						if not crit.is_inclusion and crit.snomed is not None:
							intersection = set(exclusion_codes).intersection(crit.snomed)
							if len(intersection) > 0:
								reasons = ["Matches exclusion criteria:"]
								for exc_snomed in intersection:
									reasons.append(" - %s (SNOMED %s)" % (snomed.lookup_code_meaning(exc_snomed), exc_snomed))
								reason = "\n".join(reasons)
								break
				
				if reason:
					keep.append((nct, reason))
				else:
					keep.append((nct,))
			
			runner.write_ncts(keep)
			ncts = keep
	
	# unknown filtering property
	else:
		return '{"error": "We can not filter by %s"}' % filter_by
	
	return json.dumps(ncts)


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



# start the server
if __name__ == '__main__':
	if DEBUG:
		logging.basicConfig(level=logging.DEBUG)
		bottle.run(app=app, host='0.0.0.0', port=8008, reloader=True)
	else:
		logging.basicConfig(level=logging.WARNING)
		bottle.run(app=app, host='0.0.0.0', port=8008)
