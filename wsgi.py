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
@app.get('/trials/<nct>')
def get_trial(nct):
	""" Returns one trial.
	VERY dirty for now... """
	
	run_dir = "run-server"
	if not os.path.exists(run_dir):
		bottle.abort(404)
	
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
	Study.sqlite_release_handle()
	UMLS.sqlite_handle = None
	db_path = os.path.join(run_dir, 'storage.db')
	Study.setup_tables(db_path)
	Study.setup_ctakes({'root': run_dir, 'cleanup': False})
	UMLS.import_snomed_if_necessary()
	
	# search for studies
	_write_status_for_run(run_id, "Fetching %s studies..." % condition if condition is not None else term)
	
	lilly = LillyCOI()
	if condition is not None:
		results = lilly.search_for_condition(condition, True, ['id', 'eligibility'])
	else:
		results = lilly.search_for_term(term, True, ['id', 'eligibility'])
	
	# process all studies
	run_ctakes = False
	nct = []
	for study in results:
		nct.append(study.nct)
		_write_status_for_run(run_id, "Processing %d of %d...\n" % (len(nct), len(results)))
		 
		study.load()
		study.process_eligibility_from_text()
		study.codify_eligibility()
		if study.waiting_for_ctakes():
			run_ctakes = True
		study.store()
	
	_write_ncts_for_run(run_id, nct, False)
	
	# run cTakes if needed
	if run_ctakes:
		_write_status_for_run(run_id, "Running cTakes (this will take a while)...\n")
		
		try:
			if call(['./run_ctakes.sh', run_dir]) > 0:
				_write_status_for_run(run_id, 'Error running cTakes')
				return
		except Exception, e:
			_write_status_for_run(run_id, 'Error running cTakes: %s' % e)
			return
		
		# make sure we got all criteria
		for study in results:
			study.codify_eligibility()
			study.store()
	
	Study.sqlite_commit_if_needed()
	Study.sqlite_release_handle()
	_write_status_for_run(run_id, 'done')


@app.get('/trial_runs/<run_id>/progress')
def trial_progress(run_id):
	""" Returns text status from the file corresponding to the given run-id, if
	its missing returns a 404. """
	
	status = _get_status_for_run(run_id)
	if status is None:
		bottle.abort(404)
	
	return status


def _write_status_for_run(run_id, status):
	with open('%s.status' % run_id, 'w') as handle:
		handle.write(status)

def _write_ncts_for_run(run_id, ncts, filtered=False):
	filename = '%s.%s' % (run_id, 'filtered' if filtered else 'all')
	with open(filename, 'w') as handle:
		handle.write('|'.join(set(ncts)) if ncts else '')
	

def _get_status_for_run(run_id):
	if not os.path.exists('%s.status' % run_id):
		return None
	
	with open('%s.status' % run_id) as handle:
		status = handle.readline()
	
	return status.strip() if status else None

def _get_ncts_for_run(run_id, filtered=False):
	filename = '%s.%s' % (run_id, 'filtered' if filtered else 'all')
	if not os.path.exists(filename):
		return None
	
	ncts = []
	with open(filename) as handle:
		nct_line = handle.readline()
		ncts = nct_line.strip().split('|') if nct_line else []
	
	return ncts


@app.get('/trial_runs/<run_id>/results')
def trial_results(run_id):
	""" Returns the results from a given run-id.
	Currently ignores the run-id since we only support one query at the time
	for testing purposes. """
	
	status = _get_status_for_run(run_id)
	if status is None:
		bottle.abort(404)
	
	if 'done' != status:
		bottle.abort(400, "Trial results are not available")
	
	ncts = _get_ncts_for_run(run_id, False)
	return json.dumps(ncts)

@app.get('/trial_runs/<run_id>/filter/<filter_by>')
def trial_filter_demo(run_id, filter_by):
	status = _get_status_for_run(run_id)
	if 404 == status:
		bottle.abort(404)
	
	if 'done' != status:
		bottle.abort(400, "Trial results are not available")
	
	# demographics - get age and gender
	if 'demographics' == filter_by:
		demo = demographics()
		is_male = "male" == demo.get('foaf:gender')
		bday_iso = demo.get('vcard:bday')
		bday = dateutil.parser.parse(bday_iso)		# no need for timezone correction
		age = dateutil.relativedelta.relativedelta(date.today(), bday).years
		
		ncts = _get_ncts_for_run(run_id, False)
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
		
		_write_ncts_for_run(run_id, keep, True)
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
		ncts = _get_ncts_for_run(run_id, True)
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
		
		_write_ncts_for_run(run_id, keep, True)
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
