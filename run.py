#!/usr/bin/env python
#
#	2012-12-12	Created by Pascal Pfiffner
#


import sys
from subprocess import call

from ClinicalTrials.lillycoi import LillyCOI
from ClinicalTrials.sqlite import SQLite
from ClinicalTrials.study import Study
from ClinicalTrials.umls import UMLS


CTAKES = {
	'INPUT': './ctakes_input',
	'OUTPUT': './ctakes_output'
}
UMLS_FILE = 'SnomedCT_Release_INT_20120731/RF2Release/Full/Terminology/sct2_Description_Full-en_INT_20120731.txt'


# main
if __name__ == "__main__":
	Study.setup_ctakes(CTAKES)
	Study.setup_tables()
	UMLS.setup_umls(UMLS_FILE)
	UMLS.setup_tables()
	
	# get the condition
	condition = raw_input("Condition: ")
	
	# search for studies
	print "Fetching..."
	lilly = LillyCOI()
	results = lilly.search_for(condition if condition else 'spondylitis')
	
	# process all studies
	run_ctakes = False
	print 'Processing %d results (%d)...' % (len(results), lilly.totalCount)
	for study in results:
		study.sync_with_db()
		study.process_eligibility_from_text()
		study.codify_eligibility()
		#print "%s\n-----\n%s\n^^^^^" % (study.nct, study.eligibility_formatted)
		if study.waiting_for_ctakes():
			run_ctakes = True
	
	# commit to storage
	Study.sqlite_commit_if_needed()
	
	# run cTakes
	if run_ctakes:
		print 'Running cTakes...'
		call('run_ctakes.sh')
		
		# make sure we got all criteria
		for study in results:
			study.codify_eligibility()

