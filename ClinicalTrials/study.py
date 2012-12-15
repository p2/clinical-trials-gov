#!/usr/bin/env python
#
#	Representing a ClinicalTrials.gov study
#
#	2012-12-13	Created by Pascal Pfiffner
#

import datetime
import dateutil.parser

from sqlite import SQLite
from nlp import split_inclusion_exclusion


class Study (object):
	""" Describes a study found on ClinicalTrials.gov.
	"""
	
	def __init__(self, nct=0):
		self.nct = nct
		self.updated = None
		self.gender = 0
		self.min_age = 0
		self.max_age = 200
		self.population = None
		self.healthy_volunteers = False
		self.sampling_method = None
		self.criteria_text = None
		self.criteria = []
	
	
	def from_dict(self, d):
		""" Set properties from Lilly's dictionary.
		"""
		
		# study properties
		self.nct = d.get('id')
		
		# eligibility
		e = d.get('eligibility')
		if e is not None:
			
			# gender
			gender = e.get('gender')
			if 'Both' == gender:
				self.gender = 0
			elif 'Female' == gender:
				self.gender = 2
			else:
				self.gender = 1
			
			# age
			a_max = e.get('maximum_age')
			if a_max and 'N/A' != a_max:
				self.max_age = [int(y) for y in a_max.split() if y.isdigit()][0]
			a_min = e.get('minimum_age')
			if a_min and 'N/A' != a_min:
				self.min_age = [int(y) for y in a_min.split() if y.isdigit()][0]
			
			# population and sampling
			pop = e.get('study_pop')
			self.population = pop.get('textblock') if pop else None
			self.sampling_method = e.get('sampling_method')
			self.healthy_volunteers = ('Yes' == e.get('healthy_volunteers'))
			
			# criteria
			crit = e.get('criteria')
			self.criteria_text = crit.get('textblock') if crit else None
	
	
	@property
	def eligibility_formatted(self):
		""" Puts the criteria in a human-readable format
		"""
		
		# gender
		gen = 'Both'
		if self.gender > 0:
			gen = 'Male' if 1 == self.gender else 'Female'
		
		# the main criteria
		main = self.criteria_text
		if self.criteria and len(self.criteria) > 0:
			inc = ['Inclusion Criteria:']
			exc = ['Exclusion Criteria:']
			for crit in self.criteria:
				if crit.is_inclusion:
					inc.append(crit.text)
				else:
					exc.append(crit.text)
			
			t_inc = "\n\t- ".join(inc)
			t_exc = "\n\t- ".join(exc)
			main = "%s\n\n%s" % (t_inc, t_exc)
		
		# additional bits
		return "Gender: %s\nAge: %d - %d\nHealthy: %s\n\n%s" % (
			gen, self.min_age, self.max_age,
			'Yes' if self.healthy_volunteers else 'No',
			main
		)
	
	
	# codify our plain text eligibility criteria
	def process_eligibility(self):
		if self.criteria and len(self.criteria) > 0:
			return
		
		crit = []
		
		# split into arrays
		(inclusion, exclusion) = split_inclusion_exclusion(self.criteria_text)
		
		for txt in inclusion:
			obj = StudyEligibility(self)
			obj.is_inclusion = True
			obj.text = txt
			crit.append(obj)
		
		for txt in exclusion:
			obj = StudyEligibility(self)
			obj.is_inclusion = False
			obj.text = txt
			crit.append(obj)
		
		self.criteria = crit
	
	
	# store properties to SQLite
	def store(self):
		""" Stores the receiver's data to SQLite.
		You need to MANUALLY COMMIT when you think it's appropriate!
		"""
		if self.nct is None:
			raise Exception('NCT is not set')
		
		# store our direct properties
		sql = '''REPLACE INTO studies
			(nct, updated, elig_gender, elig_min_age, elig_max_age, elig_population, elig_sampling, elig_accept_healthy, elig_criteria)
			VALUES
			(?, datetime(), ?, ?, ?, ?, ?, ?, ?)'''
		params = (
			self.nct,
			self.gender,
			self.min_age,
			self.max_age,
			self.population,
			self.sampling_method,
			self.healthy_volunteers,
			self.criteria_text
		)
		
		SQLite.execute(sql, params)
		
		# store our criteria
		for crit in self.criteria:
			crit.store()
	
	
	def load(self):
		""" Load from SQLite
		"""
		if self.nct is None:
			raise Exception('NCT is not set')
		
		# get from SQLite
		sql = '''SELECT * FROM studies WHERE nct = ?'''
		data = SQLite.executeOne(sql, (self.nct,))
		
		# populate ivars
		if data is not None:
			self.updated = dateutil.parser.parse(data[1])
			self.gender = data[2]
			self.min_age = data[3]
			self.max_age = data[4]
			self.population = data[5]
			self.sampling_method = data[6]
			self.healthy_volunteers = data[7]
			self.criteria_text = data[8]
			
			# populate parsed eligibility critiria
			self.criteria = StudyEligibility.load_for_study(self)
	
	
	@classmethod
	def setup_tables(cls):
		SQLite.create('studies', '''(
			nct UNIQUE,
			updated TIMESTAMP,
			elig_gender INTEGER,
			elig_min_age INTEGER,
			elig_max_age INTEGER,
			elig_population TEXT,
			elig_sampling TEXT,
			elig_accept_healthy INTEGER DEFAULT 0,
			elig_criteria TEXT
		)''')
		
		StudyEligibility.setup_tables()


# Study eligibility criteria management
class StudyEligibility (object):
	""" Holds one part of a study's eligibility criteria.
	Studies can have a lot of them.
	"""
	
	def __init__(self, study):
		self.id = None
		self.study = study
		self.updated = None
		self.is_inclusion = False
		self.text = None
		self.codes = []
	
	
	@classmethod
	def load_for_study(cls, study):
		""" Finds all stored criteria belonging to one study
		"""
		if study is None or study.nct is None:
			raise Exception('Study NCT is not set')
		
		found = []
		
		# find all
		sql = 'SELECT * FROM criteria WHERE study = ?'
		for rslt in SQLite.execute(sql, (study.nct,)):
			elig = StudyEligibility(study)
			elig.from_db(rslt)
			found.append(elig)
		
		return found
	
	
	def from_db(self, data):
		""" Fill from an SQLite-retrieved list
		"""
		self.id = data[0]
		self.updated = dateutil.parser.parse(data[2])
		self.is_inclusion = True if 1 == data[3] else False
		self.text = data[4]
		self.codes = data[5]
	
	
	def store(self):
		""" Stores the receiver's data to SQLite
		"""
		if self.study is None or self.study.nct is None:
			raise Exception('Study NCT is not set')
		
		# replace into
		sql = '''REPLACE INTO criteria
			(criterium_id, study, updated, is_inclusion, text, codes)
			VALUES
			(?, ?, datetime(), ?, ?, ?)'''
		params = (
			self.id,
			self.study.nct,
			1 if self.is_inclusion else 0,
			self.text,
			'|'.join(self.codes),
		)
		
		SQLite.execute(sql, params)
	
	
	@classmethod
	def setup_tables(cls):
		SQLite.create('criteria', '''(
			criterium_id INTEGER PRIMARY KEY AUTOINCREMENT,
			study TEXT,
			updated TIMESTAMP,
			is_inclusion INTEGER,
			text TEXT,
			codes TEXT
		)''')

