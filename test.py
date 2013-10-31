#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from ClinicalTrials.runner import Runner
from ClinicalTrials.umls import UMLSLookup
from ClinicalTrials.ctakes import cTAKES
from ClinicalTrials.metamap import MetaMap
from ClinicalTrials.nltktags import NLTKTags

logging.basicConfig(level=logging.DEBUG)

# setup NLP pipelines
nlp_ctakes = cTAKES()
nlp_metamap = MetaMap()
nlp_nltkt = NLTKTags()
#nlp_nltkt.cleanup = False

# setup the runner
run = Runner(666, 'run-test')
run.catch_exceptions = False
#run.limit = 3
run.discard_cached = False

run.term = "juvenile rheumatoid arthritis"
run.analyze_eligibility = False
run.analyze_properties = set(['brief_summary'])
# run.analyze_properties = set(['eligibility_inclusion', 'eligibility_exclusion', 'brief_summary', 'detailed_description'])

run.add_pipeline(nlp_metamap)
# run.add_pipeline(nlp_nltkt)

# create a callback
def cb(success, trials):
	if success:
		lookup = UMLSLookup()
		
		# loop trials
		for trial in trials:
			print 'Trial "%s"  [ %s ]' % (trial.title, trial.nct)
			d = trial.analyzable_results()
			
			# interesting categories
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
			sem_want = ['T017', 'T019', 'T020', 'T033', 'T034', 'T037', 'T047', 'T053', 'T060', 'T061', 'T121', 'T184', 'T190', 'T191']
			
			# collect wanted semantic types
			hier = {}
			
			for prop in run.analyze_properties:				# loop properties
				print "============================"
				
				d_all = d.get(prop) or {}
				for nlp_name, struct in d_all.iteritems():		# loop by NLP
					print "%s - %s" % (prop, nlp_name)
					
					d_codes = struct.get('codes', {}) if struct else {}
					for code_type, codes in d_codes.iteritems():	# by code type
						print code_type
						
						if 'cui' == code_type:
							codes = set(codes)
							code_names = []
							for cui in codes:
								lu = lookup.lookup_code(cui)
								if len(lu) > 0:
									(name, src, hier) = lu[0]
									if hier in sem_want:
										code_names.append("%s %s: %s" % (cui, hier, name))
								else:
									code_names.append(cui)
							
							print "\t%s" % "\n\t".join(code_names)
			
			print "\n"

# run!
run.run(callback=cb)


# ct = cTAKES({'root': 'run-server', 'cleanup': False})
# print ct.parse_output('51.txt')
