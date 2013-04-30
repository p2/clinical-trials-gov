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

_use_recruiting = False
_generate_report = True


# main
if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	
	# make sure we have SNOMED setup
	UMLS.import_snomed_if_necessary()
	
	# ask for a condition and recruitment status
	term = raw_input("Search for: ")
	if term is None or len(term) < 1:
		term = 'Diabetic Cardiomyopathy'
	
	recruiting = None
	if _use_recruiting:
		recruiting = raw_input("Recruiting: [no] ")
		if recruiting is None or len(recruiting) < 1:
			recruiting = False
		else:
			recruiting = recruiting[:1] is 'y' or recruiting[:1] is 'Y'
	
	# prepare a run directory
	now = date.today()
	run_dir = "run-%s-%s" % (re.sub(r'[^\w\d\-]+', '_', term.lower()), now.isoformat())
	if not os.path.exists(run_dir):
		os.mkdir(run_dir)
		os.mkdir(os.path.join(run_dir, 'ctakes_input'))
		os.mkdir(os.path.join(run_dir, 'ctakes_output'))
	
	Study.setup_ctakes({'root': run_dir, 'cleanup': False})
	
	# search for studies
	print "Fetching %s studies..." % term
	lilly = LillyCOI()
	results = lilly.search_for_term(term, recruiting, ['id', 'eligibility'])
	
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
	if _generate_report:
		print 'Generating report...'
		recr_status = ''
		if _use_recruiting:
			recr_status = ', recruiting' if recruiting else ', not recruiting'
		
		html = """<html>
		<head>
			<title>Report: %s</title>
			<style>
			body { font-size: small; font-family: 'Helvetica-Neue', Helvetica, sans-serif; }
			table { border-collapse: collapse; }
			table tbody tr td { vertical-align: top; padding: 0.15em 0.5em; }
			table tbody tr.trial_first td { padding-top: 0.5em; border-top: 1px solid #999; }
			table tbody tr td.crit_first { border-top: 1px solid #CCC; }
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
		<h1>Report for all "%s" studies %s</h1>
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
		""" % (term, term, recr_status)
		
		for study in results:
			html += study.report_row()
		
		html += """		</tbody>
		</table>
		</body>
		</html>"""
		
		handle = codecs.open('report.html', 'w', 'utf-8')
		handle.write(html)
		handle.close()

