#!/usr/bin/env python
#
#	2012-12-12	Created by Pascal Pfiffner
#


import sys
from subprocess import call
import codecs

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
	
	# ask for a condition
	condition = raw_input("Condition: ")
	if condition is None or len(condition) < 1:
		condition = 'spondylitis'
	
	# search for studies
	print "Fetching %s studies..." % condition
	lilly = LillyCOI()
	results = lilly.search_for(condition)
	
	# process all studies
	run_ctakes = False
	print 'Processing %d results (%d)...' % (len(results), lilly.totalCount)
	for study in results:
		study.sync_with_db()
		study.process_eligibility_from_text()
		study.codify_eligibility()
		if study.waiting_for_ctakes():
			run_ctakes = True
	
	Study.sqlite_commit_if_needed()
	
	# run cTakes
	if run_ctakes:
		print 'Running cTakes...'
		call('run_ctakes.sh')
		
		# make sure we got all criteria
		for study in results:
			study.codify_eligibility()
	
	# generate HTML report
	print 'Generating report...'
	html = """<html>
	<head>
		<title>Report: %s</title>
		<style>
		body { font-size: small; font-family: 'Helvetica-Neue', Helvetica, sans-serif; }
		table { border-collapse: collapse; }
		table tbody tr td { vertical-align: top; padding: 0.15em 0.5em; }
		</style>
	</head>
	<body>
	<h1>Report for all recruiting "%s" studies</h1>
	<table>
		<thead>
			<th>NCT</th>
			<th>desc</th>
			<th>text</th>
			<th></th>
			<th>SNOMED</th>
			<th></th>
		</thead>
		<tbody>
	""" % (condition, condition)
	
	for study in results:
		html += study.report_row()
	
	html += """		</tbody>
	</table>
	</body>
	</html>"""
	
	handle = codecs.open('report.html', 'w', 'utf-8')
	handle.write(html)
	handle.close()

