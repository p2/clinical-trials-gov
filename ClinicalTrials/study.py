#!/usr/bin/env python
#
#	Representing a ClinicalTrials.gov study
#
#	2012-12-13	Created by Pascal Pfiffner
#


class Study (object):
	""" Describes a study found on ClinicalTrials.gov.
	"""
	
	def __init__(self, nct):
		self.nct = nct
		self.eligibility = None

	def from_dict(self, d):
		""" Set properties from Lilly's dictionary.
		"""
		self.nct = d.get('id')
		
		elig = StudyEligibility(self)
		elig.from_dict(d.get('eligibility'))
		self.eligibility = elig


class StudyEligibility (object):
	""" Describes a study's eligibility criteria.
	"""
	
	def __init__(self, study):
		self.study = study
		self.gender = 0
		self.maxAge = 200
		self.minAge = 0
		self.population = None
		self.healthy_volunteers = False
		self.sampling_method = None
		self.criteria = None


	def from_dict(self, d):
		""" Set properties from Lilly's dictionary.
		"""
		
		# gender
		gender = d.get('gender')
		if 'Both' == gender:
			self.gender = 0
		elif 'Female' == gender:
			self.gender = 2
		else:
			self.gender = 1
		
		# age
		a_max = d.get('maximum_age')
		if a_max and 'N/A' != a_max:
			self.maxAge = [int(y) for y in a_max.split() if y.isdigit()][0]
		a_min = d.get('minimum_age')
		if a_min and 'N/A' != a_min:
			self.minAge = [int(y) for y in a_min.split() if y.isdigit()][0]
		
		# population and sampling
		pop = d.get('study_pop')
		self.population = pop.get('textblock') if pop else None
		self.sampling_method = d.get('sampling_method')
		self.healthy_volunteers = ('Yes' == d.get('healthy_volunteers'))
		
		# criteria
		crit = d.get('criteria')
		self.criteria = crit.get('textblock') if crit else None

