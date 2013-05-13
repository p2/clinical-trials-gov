#!/usr/bin/env python
#
#	cTAKES and RegEx wizardry
#
#	2012-12-14	Created by Pascal Pfiffner
#

import re
import logging


def split_inclusion_exclusion(string):
	""" Returns a tuple of lists describing inclusion and exclusion criteria.
	"""
	
	if not string or len(string) < 1:
		raise Exception('No string given')
	
	# split on newlines
	rows = re.compile("(?:\n\s*){2,}").split(string)
	
	# loop all rows
	inc = []
	exc = []
	at_inc = False
	at_exc = False
	
	for string in rows:
		if len(string) < 1 or 'none' == string:
			continue
		
		# detect switching to inclusion criteria
		if re.search('^inclusion criteria', string, re.IGNORECASE) is not None \
			and re.search('exclusion', string, re.IGNORECASE) is None:
			at_inc = True
			at_exc = False
		
		# detect switching to exclusion criteria
		elif re.search('exclusion criteria', string, re.IGNORECASE) is not None \
			and re.search('inclusion', string, re.IGNORECASE) is None:
			at_inc = False
			at_exc = True
		
		# assign accordingly
		elif at_inc:
			inc.append(string)
		elif at_exc:
			exc.append(string)
	
	# if there was no inclusion/exclusion split, we assume the text describes inclusion criteria
	if len(inc) < 1 or len(exc) < 1:
		logging.info("No explicit separation of inclusion/exclusion criteria found, assuming this text to describe inclusion criteria:")
		logging.info(string)
		inc.append(string)
	
	# join arrays back into one string
	inc = ["\n".join(inc)]
	exc = ["\n".join(exc)]
	
	return (inc, exc)


def list_to_sentences(string):
	""" Splits text at newlines and puts it back together after stripping new-
	lines and enumeration symbols, joined by a period.
	"""
	if string is None:
		return None
	
	lines = string.splitlines()
	processed = []
	for line in lines:
		processed.append(list_trim(line))
	
	return '. '.join(processed) if len(processed) > 0 else ''


def list_trim(string):
	""" Trim text phases that are part of the string because the string was
	pulled off of a list, e.g. a leading "-" or "1."
	"""
	
	string.strip()
	string = re.sub('\s+', ' ', string)						# multi-whitespace
	string = re.sub('^-\s+', '', string, count=1)			# leading "-"
	string = re.sub('^\d+\.\s+', '', string, count=1)		# leading "1."
	
	return string

