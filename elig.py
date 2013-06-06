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

from ClinicalTrials.runner import Runner

_use_recruiting = False
_generate_report = True


# main
if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	
	# ask for a condition and recruitment status
	term = raw_input("Search for: ")
	if term is None or len(term) < 1:
		term = 'diabetic cardiomyopathy'
	
	# recruiting = None
	# if _use_recruiting:
	# 	recruiting = raw_input("Recruiting: [no] ")
	# 	if recruiting is None or len(recruiting) < 1:
	# 		recruiting = False
	# 	else:
	# 		recruiting = recruiting[:1] is 'y' or recruiting[:1] is 'Y'
	
	# run the runner
	now = date.today()
	run_id = now.isoformat()
	run_dir = "run-%s-%s" % (re.sub(r'[^\w\d\-]+', '_', term.lower()), run_id)
	runner = Runner(run_id ,run_dir)
	runner.run_ctakes = True
	runner.run_metamap = True
	runner.term = term
	runner.log_status = True
	runner.run()
	
	# generate HTML report
	if _generate_report:
		print 'Generating report...'
		recr_status = ''
		if _use_recruiting:
			recr_status = ', recruiting' if recruiting else ', not recruiting'
		
		html = """<html>
		<head>
			<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
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
				<tr>
					<th></th>
					<th></th>
					<th></th>
					<th></th>
					<th colspan="4">cTAKES</th>
					<th colspan="2">MetaMap</th>
				</tr>
				<tr>
					<th>NCT</th>
					<th>raw</th>
					<th>text</th>
					<th></th>
					<th>SNOMED</th>
					<th></th>
					<th>RxNorm</th>
					<th></th>
					<th>CUI</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
		""" % (term, term, recr_status)
		
		for study in runner.found_studies:
			html += study.report_row()
		
		html += """		</tbody>
		</table>
		</body>
		</html>"""
		
		report_path = os.path.join(run_dir, 'report.html')
		handle = codecs.open(report_path, 'w', 'utf-8')
		handle.write(html)
		handle.close()
		
		print "Wrote report to %s" % report_path

