#!/usr/bin/env python
#
#	2012-12-12	Created by Pascal Pfiffner
#

import os
import re
import sys
from subprocess import call
import codecs
import logging
from datetime import date

from ClinicalTrials.lillycoi import LillyCOI
from ClinicalTrials.sqlite import SQLite
from ClinicalTrials.study import Study
from ClinicalTrials.umls import UMLS


# main
if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	
	# make sure we have SNOMED setup
	UMLS.import_snomed_if_necessary()
	
	# ask for a condition
	recruiting = False
	condition = raw_input("Condition: ")
	if condition is None or len(condition) < 1:
		condition = 'spondylitis'
	
	# prepare a run directory
	now = date.today()
	run_dir = "run-%s-%s" % (re.sub(r'[^\w\d\-]+', '_', condition), now.isoformat())
	if not os.path.exists(run_dir):
		os.mkdir(run_dir)
		os.mkdir(os.path.join(run_dir, 'ctakes_input'))
		os.mkdir(os.path.join(run_dir, 'ctakes_output'))
	
	Study.setup_ctakes({'root': run_dir, 'cleanup': False})
	
	# search for studies
	print "Fetching %s studies..." % condition
	lilly = LillyCOI()
	results = lilly.search_for(condition, recruiting)
	
	# process all studies
	run_ctakes = False
	i = 0
	for study in results:
		i += 1
		print 'Processing %d of %d...' % (i, len(results))
		study.load()
		study.process_eligibility_from_text()
		study.run_pmc(run_dir)
		study.codify_eligibility()
		if study.waiting_for_ctakes():
			run_ctakes = True
		study.store()
	
	Study.sqlite_commit_if_needed()
	
	# run cTakes if needed
	if run_ctakes:
		print 'Running cTakes...'
		call(['run_ctakes.sh', run_dir])
		
		# make sure we got all criteria
		for study in results:
			study.codify_eligibility()
	
	Study.sqlite_commit_if_needed()
	
	# generate HTML report
	if True:
		print 'Generating report...'
		html = """<html>
		<head>
			<title>Report: %s</title>
			<style>
			body { font-size: small; font-family: 'Helvetica-Neue', Helvetica, sans-serif; }
			table { border-collapse: collapse; }
			table tbody tr td { vertical-align: top; padding: 0.15em 0.5em; }
			</style>
			<script>
			function toggle(td) {
				var div = td.getElementsByTagName('div')[0];
				if ('none' == div.style.display) {
					div.style.display = 'block';
				}
				else {
					div.style.display = 'none';
				}
			}
			</script>
		</head>
		<body>
		<h1>Report for all recruiting "%s" studies</h1>
		<table>
			<colgroup>
				<col />
				<col />
				<col width="40%%" />
				<col />
				<col />
				<col />
			</colgroup>
			<thead>
				<th>NCT</th>
				<th>raw</th>
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

