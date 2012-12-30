#!/usr/bin/env python
#
#	2012-12-12	Created by Pascal Pfiffner
#


from ClinicalTrials.lillycoi import LillyCOI
from ClinicalTrials.sqlite import SQLite
from ClinicalTrials.study import Study

CTAKES = {
	'INPUT': '../input',
	'OUTPUT': '../output'
}


# main
if __name__ == "__main__":
	
	# get the condition
	condition = raw_input("Condition: ")
	
	# search for studies
	print "Fetching..."
	lilly = LillyCOI()
	results = lilly.search_for(condition if condition else 'spondylitis')
	
	# setup studies
	Study.setup_tables()
	Study.setup_ctakes(CTAKES)
	
	# process all studies
	run_ctakes = False
	print 'Processing %d results (%d)...' % (len(results), lilly.totalCount)
	for study in results:
		study.sync_with_db()
		study.process_eligibility()
		study.codify_eligibility()
		#print "%s\n-----\n%s\n^^^^^" % (study.nct, study.eligibility_formatted)
		if study.waiting_for_ctakes():
			run_ctakes = True
	
	# commit to storage
	SQLite.commit()
	
	# run cTakes
	if run_ctakes:
		print 'Running cTakes...'
		

