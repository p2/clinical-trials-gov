#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#	Handling cTAKES
#
#	2013-05-14	Created by Pascal Pfiffner
#

import os
import logging
import codecs

from xml.dom.minidom import parse

from nlp import NLPProcessing, list_to_sentences


class MetaMap (NLPProcessing):
	""" Aggregate handling tasks specifically for MetaMap. """
	
	def __init__(self, settings):
		super(MetaMap, self).__init__(settings)
		self.name = 'metamap'
	
	
	def write_input(self, text, filename):
		if text is None or len(text) < 1:
			return False
		
		in_file = os.path.join(self.root if self.root is not None else '.', 'metamap_input')
		if not os.path.exists(in_file):
			logging.error("The input directory for MetaMap does not exist")
			return False
		
		infile = os.path.join(in_file, filename)
		if os.path.exists(infile):
			return False
		
		# write it
		with codecs.open(infile, 'w', 'utf-8') as handle:
			handle.write(list_to_sentences(text))
		
		return True
	
	
	def parse_output(self, filename):
		""" Parse MetaMap XML output. """
		if filename is None:
			return (None, None)
		
		# is there output?
		root = self.root if self.root is not None else '.'
		out_dir = os.path.join(root, 'metamap_output')
		if not os.path.exists(out_dir):
			logging.error("The output directory for MetaMap at %s does not exist" % out_dir)
			return (None, None)
		
		outfile = os.path.join(out_dir, filename)
		if not os.path.exists(outfile):
			return (None, None)
		
		snomeds = []
		cuis = []
		
		# parse XMI file
		root = parse(outfile).documentElement
		
		# find mappings
		candidates = []
		try:
			foo = root.getElementsByTagName('MMO')[0].getElementsByTagName('Utterances')[0]
			utterances = foo.getElementsByTagName('Utterance')
			for utter in utterances:
				phrases = utter.getElementsByTagName('Phrases')[0].getElementsByTagName('Phrase')
				for phrase in phrases:
					candidates = phrase.getElementsByTagName('Candidates')[0].getElementsByTagName('Candidate')
					
					# also get the mapping candidate candidates
					mappings = phrase.getElementsByTagName('Mappings')[0].getElementsByTagName('Mapping')
					for mapping in mappings:
						for cand in mapping.getElementsByTagName('MappingCandidates'):
							candidates.extend(cand.getElementsByTagName('Candidate'))
		except Exception, e:
			pass
		
		# pull out codes
		for candidate in candidates:
			# matchNodes = candidate.getElementsByTagName('CandidateMatched')
			# if 1 != len(matchNodes):
			# 	logginge.error("Only expecting one CandidateMatched node, but got %d" % len(matchNodes))
			# 	continue
			# match = matchNodes[0]
			# if 1 != len(match.childNodes):
			# 	logginge.error("Only expecting one child node in our CandidateMatched node, but got %d" % len(match.childNodes))
			# 	continue
			
			cuiNodes = candidate.getElementsByTagName('CandidateCUI')
			if 1 != len(cuiNodes):
				logginge.error("Only expecting one CandidateCUI node, but got %d" % len(cuiNodes))
				continue
			cuiN = cuiNodes[0]
			if 1 != len(cuiN.childNodes):
				logginge.error("Only expecting one child node in our CandidateCUI node, but got %d" % len(cuiN.childNodes))
				continue
			
			#print "%s: %s" % (match.childNodes[0].nodeValue, cuiN.childNodes[0].nodeValue)
			cui = cuiN.childNodes[0].nodeValue
			if cui is not None:
				cuis.append(cui)
		
		# clean up if instructed to do so
		if self.cleanup:
			os.remove(outfile)
			
			in_dir = os.path.join(root, 'metamap_input')
			infile = os.path.join(in_dir, filename)
			if os.path.exists(infile):
				os.remove(infile)
		
		return (snomeds, cuis)

