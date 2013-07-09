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
from settings import USE_APP_ID, USE_SMART_05, USE_NLP, GOOGLE_API_KEY, DEBUG, ENDPOINTS
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
		logging.info("There is no session")
		return None
	
	# configure SMART client
	api_base = sess.get('api_base')
	if not api_base:
		logging.info("No api_base is set")
		return None
	
	# find server credentials and store in session
	cons_key = sess.get('consumer_key')
	cons_sec = sess.get('consumer_secret')
	if not cons_key or not cons_sec:
		server = None
		for ep in ENDPOINTS:
			if ep.get('url') == api_base:
				server = ep
				break
		
		if server is None:
			logging.error("There is no server with base URI %s" % api_base)
			return None
		
		sess['consumer_key'] = cons_key = server.get('consumer_key')
		sess['consumer_secret'] = cons_sec = server.get('consumer_secret')
	
	# init client
	config = {
		'consumer_key': cons_key,
		'consumer_secret': cons_sec
	}
	
	try:
		smart = SMARTClient(USE_APP_ID, api_base, config)
		smart.record_id = sess.get('record_id')
	except Exception, e:
		logging.warning("Failed to instantiate SMART client: %s" % e)
		smart = None
	
	# if we have tokens, update the client
	token = sess.get('token')
	if token is not None:
		smart.update_token(token)
	
	return smart

def _test_record_token():
	""" Tries to fetch demographics with the given token and returns a bool
	whether thas was successful. """
	
	smart = _get_smart()
	if smart is None:
		return False
	
	# try to get demographics
	try:
		ret = smart.get_demographics()
		
		# did work!
		if 200 == int(ret.response.status):
			return True
	except Exception, e:
		pass
	
	return False

def _reset_session(with_runs=False):
	""" Removes patient-related session settings. """
	sess = _get_session()
	
	if 'record_id' in sess:
		del sess['record_id']
	if 'token' in sess:
		del sess['token']
	
	# clear run data
	if with_runs:
		if 'runs' in sess:
			del sess['runs']
	
	# SMART 0.5 hacks
	if USE_SMART_05:
		if 'demographics' in sess:
			del sess['demographics']
		if 'problems' in sess:
			del sess['problems']

# ------------------------------------------------------------------------------ Index
@bottle.get('/')
@bottle.get('/index.html')
def index():
	""" The index page """
	sess = _get_session()
	
	# look at URL params first, if they are there store them in the session
	api_base = bottle.request.query.get('api_base')
	if api_base is not None:
		sess['api_base'] = api_base
	else:
		api_base = sess.get('api_base')
	
	# no endpoint, show selector
	if not api_base:
		_reset_session()
		logging.debug('redirecting to endpoint selection')
		bottle.redirect('endpoint_select')
	
	# determine record id
	record_id = bottle.request.query.get('record_id')
	if record_id is not None:
		old_id = sess.get('record_id')
		
		# reset session if we get a new record (or none)
		if old_id != record_id:
			_reset_session()
		
		# set (or don't) the record id
		if '0' != record_id:
			sess['record_id'] = record_id
		else:
			record_id = None
	else:
		record_id = sess.get('record_id')
	
	smart = _get_smart()
	if smart is None:
		return "Cannot connect to SMART sandbox"
	
	# no record id, call launch page
	if record_id is None:
		launch = smart.launch_url
		if launch is None:
			return "Unknown app start URL, cannot launch"
		
		logging.debug('redirecting to app launch page')
		bottle.redirect(launch)
		return
	
	# still here, test the token
	if not _test_record_token():
		smart.token = None
		try:
			sess['token'] = smart.fetch_request_token()
		except Exception, e:
			_reset_session()
			logging.error("Failed getting request token. %s" % e)
			return "Failed to obtain access permissions, please reload"
		
		# now go and authorize the token
		logging.debug("Have request token, redirecting to authorize token")
		bottle.redirect(smart.auth_redirect_url)
		return
	
	# everything in order, render index
	template = _jinja_templates.get_template('index.html')
	defs = {
		'smart_v05': USE_SMART_05,
		'google_api_key': GOOGLE_API_KEY
	}
	
	return template.render(defs=defs, has_chrome=False, api_base=api_base, last_manual_condition=sess.get('last_manual_condition'))


@bottle.get('/authorize')
def authorize():
	""" Extract the oauth_verifier from the callback and exchange it for an
	access token. """
	
	verifier = bottle.request.query.get('oauth_verifier')
	
	# exchange
	smart = _get_smart()
	if smart is None:
		return "Cannot connect to SMART sandbox"
	
	try:
		sess = _get_session()
		sess['token'] = smart.exchange_token(verifier)
	except Exception, e:
		logging.error("Token exchange failed: %s" % e)
		return str(e)
	
	# looks good!
	logging.debug("Got an access token, returning home")
	bottle.redirect('/index.html?api_base=%s&record_id=%s' % (sess['api_base'], sess['record_id']))


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
	
	demo_ld = None
	d = {}	
	
	# SMART 0.5 fallback (the JS client writes demographics to session storage)
	if USE_SMART_05:
		sess = _get_session()
		demo_rdf = sess.get('demographics') if sess is not None else None
		
		# use session data (parse RDF, convert to json-ld-serialization, load json... :P)
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
	
	# SMART 0.6+
	else:
		smart = _get_smart()
		if not smart:
			return d
		
		ret = smart.get_demographics()
		if 200 == int(ret.response.status):
			demo_ld = json.loads(ret.graph.serialize(format='json-ld')) if ret.graph is not None else None
		else:
			logging.error("Failed to get demographics: %d" % ret.response.status)
	
	# extract interesting pieces
	if demo_ld is not None:
		for gr in demo_ld.get("@graph", []):
			if "sp:Demographics" == gr.get("@type"):
				d = gr
				break
	
	return d


@bottle.get('/problems')
def problems():
	""" Returns the current patient's problems as JSON extracted from JSON-LD.
	"""
	
	prob_ld = None

	# SMART 0.5 fallback (the JS client writes problem data to session storage)
	if USE_SMART_05:
		sess = _get_session()
		prob_rdf = sess.get('problems') if sess is not None else None
		
		# use session data (parse RDF, convert to json-ld-serialization, load json... :P)
		try:
			graph = Graph().parse(data=prob_rdf)
		except Exception, e:
			logging.error("Failed to parse problems: %s\n%s" % (e, prob_rdf))
			return {'problems': []}
		
		prob_ld = json.loads(graph.serialize(format='json-ld'))
	
	# SMART 0.6+
	else:
		smart = _get_smart()
		ret = smart.get_problems()
		if 200 == int(ret.response.status):
			prob_ld = json.loads(ret.graph.serialize(format='json-ld')) if ret.graph is not None else None
		else:
			logging.error("Failed to get problems: %d" % ret.response.status)
	
	# pick out the individual problems
	problems = []
	for gr in prob_ld.get("@graph", []):
		if "sp:Problem" == gr.get("@type"):
			problems.append(gr)
	
	return {'problems': problems}


# ------------------------------------------------------------------------------ Trials
@bottle.get('/trials/<nct_list>')
def get_trial(nct_list):
	""" Returns one or more trials, multiple NCTs can be separated by colon. """
	trials = []
	
	if nct_list:
		ncts = nct_list.split(':')
		for nct in ncts:
			trial = Study(nct)
			trial.load()
			trials.append(trial.json(['brief_summary', 'location', 'intervention', 'study_design']))
	
	return {'trials': trials}


@bottle.get('/trial_runs')
def find_trials():
	""" Initiates the chain to find trials for the given condition or search-
	term. Supply with parameters:
	- "cond" or "term", the prior taking precedence
	- "gender" ('male' or 'female')
	- "age" (in years)
	- "remember_cond" if the condition should be stored in the session
	
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
	
	# store in session
	sess = _get_session()
	runs = sess.get('runs', {})
	runs[run_id] = {
		'cond': cond,
		'gender': bottle.request.query.get('gender'),
		'age': int(bottle.request.query.get('age'))
	}
	sess['runs'] = runs
	
	if bottle.request.query.get('remember_cond'):
		if cond:
			sess['last_manual_condition'] = cond
		elif 'last_manual_condition' in sess:
			del sess['last_manual_condition']
	
	# launch and return id
	runner.run(['id', 'acronym', 'brief_title', 'official_title', 'brief_summary', 'eligibility', 'location', 'attributes', 'intervention', 'intervention_browse', 'phase', 'study_design'])
	
	return run_id


@bottle.get('/trial_runs/<run_id>/progress')
def trial_progress(run_id):
	""" Returns text status from the file corresponding to the given run-id, if
	it's missing returns a 404. """
	
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
	sess = _get_session()
	run_data = sess.get('runs', {}).get(run_id, {})
	
	# demographics - get age and gender
	if 'demographics' == filter_by:
		f_gender = run_data.get('gender')
		f_age = int(run_data.get('age', 0))
		
		keep = []
		for tpl in ncts:
			nct = tpl[0]
			reason = tpl[1] if len(tpl) > 1 else None
			
			if not reason:
				trial = Study(nct)
				trial.load()
				
				# filter gender
				if 'male' == f_gender:
					if trial.gender == 2:
						reason = "Limited to women"
				else:
					if trial.gender == 1:
						reason = "Limited to men"
				
				# filter age
				if trial.min_age > f_age:
					reason = "Patient is too young (min age %d)" % trial.min_age
				elif trial.max_age < f_age:
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
				
				# if we already have a reason, this trial has already been filtered
				if not reason:
					trial = Study(nct)
					trial.load()
					for crit in trial.criteria:
						
						# check exclusion criteria
						if not crit.is_inclusion and crit.snomed is not None:
							match = None
							for snomed_c in crit.snomed:
								if '-' != snomed_c[0:1]:		# SNOMED codes starting with a minus were negated
									match = snomed_c if snomed_c in exclusion_codes else None
							
							# exclusion criterion matched
							if match is not None:
								reason = 'Matches exclusion criterium "%s" (SNOMED %s)'  % (snomed.lookup_code_meaning(match, True, True), match)
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
