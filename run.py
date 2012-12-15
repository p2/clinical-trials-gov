#!/usr/bin/env python
#
#	2012-12-12	Created by Pascal Pfiffner
#


from ClinicalTrials.lillycoi import LillyCOI
from ClinicalTrials.sqlite import SQLite
from ClinicalTrials.study import Study


# main
if __name__ == "__main__":
	
	# get the condition
	condition = raw_input("Condition: ")
	
	# search for studies
	print "Fetching..."
	lilly = LillyCOI()
	results = lilly.search_for(condition if condition else 'spondylitis')
	print 'Num results: %d (%d)' % (lilly.totalCount, len(results))
	
	# process all studies
	Study.setup_tables()
	
	for study in results:
		study.load()
		study.process_eligibility()
		#print "%s\n-----\n%s\n^^^^^" % (study.nct, study.eligibility_formatted)
		study.store()
	
	# commit to storage
	SQLite.commit()

