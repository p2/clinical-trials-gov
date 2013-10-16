#!/usr/bin/python

import logging
from ClinicalTrials.runner import Runner
from ClinicalTrials.umls import UMLSLookup

logging.basicConfig(level=logging.DEBUG)

# setup the runner
run = Runner(666, 'run-test')
#run.term = "diabetic cardiomyopathy"
run.term = "juvenile rheumatoid arthritis"
run.analyze_eligibility = False
run.analyze_properties = set(['brief_summary', 'detailed_description'])
run.run_metamap = True

# create a callback
def cb(success, trials):
	if success:
		lookup = UMLSLookup()
		
		# loop trials
		for trial in trials:
			print 'Trial "%s"  [ %s ]' % (trial.title, trial.nct)
			d = trial.analyzable_results()
			
			# - T017: Anatomical Structure
			# - T019: Congenital Abnormality
			# - T020: Acquired Abnormality
			# - T033: Finding
			# - T034: Laboratory or Test Result
			# - T037: Injury or Poisoning
			# - T047: Disease or Syndrome
			# - T053: Behavior
			# - T060: Diagnostic Procedure
			# - T061: Therapeutic or Preventive Procedure
			# - T121: Pharmacologic Substance
			# - T184: Sign or Symptom
			# - T190: Anatomical Abnormality
			# - T191: Neoplastic Process
			sem_want = None #['T047']
			
			# collect wanted semantic types
			hier = {}
			for prop in run.analyze_properties:
				d_flat = d.get(prop) or {}
				cuis_flat = d_flat.get('cui_metamap') or []
				
				# lookup CUIs
				hier_wanted = {}
				for cui in set(cuis_flat):
					for name, src, sem in lookup.lookup_code(cui):
						string = "%s [%s]" % (name, cui)
						if sem in hier_wanted:
							hier_wanted[sem].append(string)
						elif sem_want is None or sem in sem_want:
							hier_wanted[sem] = [string]
				hier[prop] = hier_wanted
			
			# print hierarchy
			for prop in run.analyze_properties:
				print prop
				hier_prop = hier[prop]
				for sty, arr in hier_prop.iteritems():
					print "\t%s:" % sty
					for name in arr:
						print "\t\t%s" % name
				print "============================"
			print "\n"

# run!
run.run(callback=cb)


# from ClinicalTrials.ctakes import cTAKES
# ct = cTAKES({'root': 'run-server', 'cleanup': False})
# print ct.parse_output('51.txt')
