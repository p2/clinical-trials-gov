#!/usr/bin/python
# -*- coding: utf-8 -*-

# NCT01954979


from ClinicalTrials.study import Study

# loop trials
trials = Study.retrieve(['NCT01954979'])
for trial in trials:
	print '-> ', trial.title
	codifieds = trial.codified_properties()
	if codifieds is None or 0 == len(codifieds):
		print 'xx>  No codified data'
		continue
	
	# look at codified data
	for prop, codified in codifieds.iteritems():
		if len(codified) > 0:
			for nlp_name, res in codified.iteritems():
				
				# MetaMap
				if 'metamap' == nlp_name:
					codes = res.get('codes')
					if codes:
						text = codes.get('text')
						cuis = codes.get('cui')
						
						# sort cuis by location
						sorted_cuis = []
						for cui in cuis:
							pass
						
						# loop through
						for cui in sorted_cuis:
							pass
						
