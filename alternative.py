#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from ClinicalTrials.runner import Runner

logging.basicConfig(level=logging.DEBUG)

# setup the runner
run = Runner(666, 'run-alternative')
run.catch_exceptions = False
#run.limit = 3
run.discard_cached = False

run.term = "pulmonary arterial hypertension"
# run.term = "juvenile rheumatoid arthritis"
run.analyze_eligibility = False
run.analyze_keypaths = set(['condition_browse', 'intervention_browse', 'intervention', 'keyword', 'primary_outcome', 'arm_group'])

# create a callback
def cb(success, trials):
	if success:
		
		# loop trials
		for trial in trials:
			doc = trial.doc or {}
			print 'Trial "%s"  [ %s ]' % (trial.title, trial.nct)
			print '    keyw: %s' % '; '.join(doc.get('keyword') or [])
			print '    cond: %s' % '; '.join(doc.get('condition_browse', {}).get('mesh_term', []))
			print '    intr: %s' % '; '.join(doc.get('intervention_browse', {}).get('mesh_term', []))
			print '    intn: %s' % "\n    ----> ".join([p.get('intervention_name') or '' for p in doc.get('intervention', [])])
			print '    prim: %s' % "\n    ----> ".join([p.get('measure') or '' for p in doc.get('primary_outcome', [])])
		#	print '    armg: %s' % "\n    ----> ".join([a.get('description') or '' for a in doc.get('arm_group', [])])
			
			print "\n"

# run!
print 'Run id %d' % run.run_id
run.run(callback=cb)
