#!/usr/bin/env python
#
#	Representing a ClinicalTrials.gov study
#
#	2012-12-13	Created by Pascal Pfiffner
#

import datetime
import dateutil.parser
import os.path
import codecs

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
	
	
	# extract single criteria from plain text eligibility criteria
	def process_eligibility(self):
		""" Does nothing if the "criteria" property already holds at least one
		StudyEligibility object, otherwise parses "criteria_text" into such
		objects.
		"""
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
		self.store_criteria()
	
	
	# assigns codes to all eligibility criteria
	def codify_eligibility(self):
		""" Retrieves the codes from SQLite or, if there are none, passes the
		text criteria to cTakes.
		"""
		if self.criteria and len(self.criteria) > 0:
			for criterium in self.criteria:
				criterium.codify()
	
	
	def waiting_for_ctakes(self):
		""" Returns True if any of our criteria needs to run through cTakes.
		"""
		if self.criteria and len(self.criteria) > 0:
			for criterium in self.criteria:
				if criterium.waiting_for_ctakes:
					return True
		
		return False
	
	
	# loads and stores
	def sync_with_db(self):
		""" Loads from SQLite and stores again.
		Don't forget to commit manually at one point!
		"""
		self.load()
		self.store()
	
			
	# store properties to SQLite
	def store(self):
		""" Stores the receiver's properties, including all StudyEligibility
		objects, to SQLite.
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
		
		return SQLite.execute(sql, params)
	
	
	def store_criteria(self):
		""" Stores our criteria to SQLite.
		"""
		if self.criteria and len(self.criteria) > 0:
			for criterium in self.criteria:
				criterium.store()
	
	
	def load(self):
		""" Load from SQLite.
		Will fill all stored properties and load all StudyEligibility belonging
		to this study into the "criteria" property.
		"""
		if self.nct is None:
			raise Exception('NCT is not set')
		
		# get from SQLite
		sql = 'SELECT * FROM studies WHERE nct = ?'
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
			
			# populate parsed eligibility criteria
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
	
	@classmethod
	def setup_ctakes(cls, setting):
		StudyEligibility.CTAKES = setting




# Study eligibility criteria management
class StudyEligibility (object):
	""" Holds one part of a study's eligibility criteria.
	Studies can have a lot of them.
	"""
	
	def __init__(self, study):
		self.id = None
		self.hydrated = False
		self.study = study
		self.updated = None
		self.is_inclusion = False
		self.text = None
		self.codes = []
		self.has_been_parsed = False
		self.waiting_for_ctakes = False
	
	
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
			elig.hydrated = True
			found.append(elig)
		
		return found
	
	
	def from_db(self, data):
		""" Fill from an SQLite-retrieved list.
		"""
		self.id = data[0]
		self.updated = dateutil.parser.parse(data[2])
		self.is_inclusion = True if 1 == data[3] else False
		self.text = data[4]
		self.codes = data[5].split('|') if data[5] else None
		self.has_been_parsed = (1 == data[6])
	
	
	def codify(self):
		""" Three stages:
		      1. Reads the codes from SQLite, if they are there
		      2. Reads and stores the codes from the cTakes output dir, if they
		         are there
		      3. Writes the criteria to the cTakes input directory
		"""
		if self.codes and len(self.codes) > 0:
			return
		
		# 1. no codes and not hydrated, fetch from SQLite
		if not self.hydrated:
			raise Exception('not implemented')
		
		# 2. not there, look in cTakes OUTPUT directory
		ct = StudyEligibility.CTAKES
		if ct['OUTPUT'] and os.path.exists(ct['OUTPUT']):
			myfile = os.path.join(ct['OUTPUT'], '%d.txt' % self.id)
			if os.path.exists(myfile):
				lines = [line.strip() for line in codecs.open(myfile, 'r', 'utf-8')]
				self.codes = lines.split('|') if len(lines) > 0 else None
				close(myfile)
				# TODO: remove the files in input and output!
				return
		
		# 3. not yet processed, put it there and wait for cTakes to process it
		if ct['INPUT'] and os.path.exists(ct['INPUT']):
			myfile = os.path.join(ct['INPUT'], '%d.txt' % self.id)
			if not os.path.exists(myfile):
				handle = codecs.open(myfile, 'w', 'utf-8')
				handle.write(self.text)
				handle.close()
			self.waiting_for_ctakes = True
	
	
	def store(self):
		""" Stores the receiver's data to SQLite.
		"""
		if self.study is None or self.study.nct is None:
			raise Exception('Study NCT is not set')
		
		# insert if we don't have an id
		if self.id is None:
			sql = '''INSERT OR IGNORE INTO criteria
				(criterium_id, study) VALUES (?, ?)'''
			params = (
				self.id,
				self.study.nct
			)
			self.id = SQLite.executeInsert(sql, params)
		
		# update the remaining stuff
		sql = '''UPDATE criteria SET
			updated = datetime(), is_inclusion = ?, text = ?, codes = ?
			WHERE criterium_id = ?'''
		params = (
			1 if self.is_inclusion else 0,
			self.text,
			'|'.join(self.codes),
			self.id
		)
		
		if SQLite.execute(sql, params):
			self.hydrated = True
			return True
		
		return False
	
	
	@classmethod
	def setup_tables(cls):
		SQLite.create('criteria', '''(
			criterium_id INTEGER PRIMARY KEY AUTOINCREMENT,
			study TEXT,
			updated TIMESTAMP,
			is_inclusion INTEGER,
			text TEXT,
			codes TEXT,
			has_been_parsed INTEGER DEFAULT 0
		)''')

