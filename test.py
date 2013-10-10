#!/usr/bin/python

import logging
from ClinicalTrials.runner import Runner

logging.basicConfig(level=logging.DEBUG)

# setup the runner
run = Runner(666, 'run-test')
run.term = "diabetic cardiomyopathy"
run.analyze_eligibility = False
run.analyze_properties = set(['brief_summary', 'detailed_description'])
run.run_metamap = True

# create a callback
def cb(success, trials):
	if success:
		for trial in trials:
			print trial.analyzable_results()

# run!
run.run(callback=cb)


# from ClinicalTrials.ctakes import cTAKES
# ct = cTAKES({'root': 'run-server', 'cleanup': False})
# print ct.parse_output('51.txt')
