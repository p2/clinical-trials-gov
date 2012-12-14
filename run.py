#!/usr/bin/env python
#
#	2012-12-12	Created by Pascal Pfiffner
#


from ClinicalTrials.lillycoi import LillyCOI


# main
if __name__ == "__main__":
    lilly = LillyCOI()
    
    # get the condition
    condition = raw_input("Condition: ")
    
    # search
    print "Fetching..."
    results = lilly.search_for(condition if condition else 'spondylitis')
    print 'Num results: %d (%d)' % (lilly.totalCount, len(results))
    
    # debug
    for study in results:
        print '->  %s: %d-%d' % (study.nct, study.eligibility.minAge, study.eligibility.maxAge)

