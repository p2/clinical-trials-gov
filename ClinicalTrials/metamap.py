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

