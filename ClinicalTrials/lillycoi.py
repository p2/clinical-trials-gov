#!/usr/bin/env python
#
#	Talk to ClinicalTrials.gov via Lilly's API
#	http://portal.lillycoi.com/api-reference-guide/
#
#	2012-12-12	Created by Pascal Pfiffner
#

import httplib2
import json

from study import Study


class LillyCOI (object):
	baseURL = 'http://api.lillycoi.com/v1'


	# initialization
	def __init__(self):
		self.http = httplib2.Http()
		self.previousPageURI = None
		self.nextPageURI = None
		self.resultCount = 0
		self.totalCount = 0


	# count results
	def num_results_for(self, condition, recruiting=True):
		cond = condition.replace(' ', '-')
		recr = 'open' if recruiting is True else 'closed'
		params = 'fields=id&limit=1&query=recr:%s,cond:%s' % (recr, cond)
		return self.get('trials/search.json', params)


	# searching for trials
	def search_for(self, condition, recruiting=True):
		cond = condition.replace(' ', '-')
		recr = 'open' if recruiting is True else 'closed'
		params = 'fields=id,eligibility&limit=20&query=recr:%s,cond:%s' % (recr, cond)		# bug in Lilly's API, first page only returns at max 20 results, so don't go higher
		
		# loop page after page
		results = self.get('trials/search.json', params)
		while self.nextPageURI is not None:
			results.extend(self._get(self.nextPageURI))
		
		return results


	# using GET to retrieve data
	def get(self, method, parameters=None):
		"""Performs a GET request against Lilly's base URL and decodes the JSON
		to a dictionary/array representation.
		"""
		
		url = '%s/%s' % (LillyCOI.baseURL, method)
		if parameters is not None:
			url = '%s?%s' % (url, parameters)
		return self._get(url)


	# the base GET grabber
	def _get(self, url):
		#print '-->  GET: %s' % url
		headers = {}
		
		# fire it off
		response, content = self.http.request(url, 'GET', headers=headers)
		
		# decode JSON
		data = {}
		try:
			data = json.loads(content)
		except Exception, e:
			print "-----\n%s\n-----\n%s\n-----" % (e, content)
			return []
		
		self.previousPageURI = data.get('previousPageURI')
		self.nextPageURI = data.get('nextPageURI')
		self.resultCount = data.get('resultCount')
		self.totalCount = data.get('totalCount')
		
		#print '==>  got: %d' % len(data.get('results', []))
		
		# instantiate study objects
		studies = []
		for s in data.get('results', []):
			study = Study(0)
			study.from_dict(s)
			studies.append(study)
		
		return studies

