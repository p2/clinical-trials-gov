#!/usr/bin/env python
#
#	Representing a ClinicalTrials.gov study
#
#	2012-12-13	Created by Pascal Pfiffner
#

import datetime
import dateutil.parser
import os
import codecs
from xml.dom.minidom import parse

from sqlite import SQLite
from nlp import split_inclusion_exclusion
from umls import UMLS


class Study (object):
	""" Describes a study found on ClinicalTrials.gov.
	"""
	
	sqlite_handle = None
	sqlite_must_commit = False
	
	
	def __init__(self, nct=0):
		self.nct = nct
		self.hydrated = False
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
	
	
	def report_row(self):
		""" Generates an HTML row for the report_row document.
		"""
		if self.criteria is None or len(self.criteria) < 1:
			return ''
		
		# collect criteria
		rows = []
		for crit in self.criteria:
			
			# this criterium has been codified
			if len(crit.snomed) > 0:
				c_html = '<td rowspan="%d">%s</td><td rowspan="%d">%s</td>' % (len(crit.snomed), crit.text, len(crit.snomed), 'in' if crit.is_inclusion else 'ex')
				for sno in crit.snomed:
					rows.append(c_html + '<td>%s</td><td>%s</td>' % (sno, UMLS.lookup_snomed(sno)))
					if len(c_html) > 0:
						c_html = ''
			
			# no codes for this criterium
			else:
				rows.append('<td>%s</td><td>%s</td><td></td>' % (crit.text, 'in' if crit.is_inclusion else 'ex'))
		
		if len(rows) < 1:
			return ''
		
		# compose HTML
		html = """<tr>
		<td rowspan="%d">
			<a href="http://clinicaltrials.gov/ct2/show/%s" target="_blank">%s</a>
		</td>
		<td rowspan="%d" onclick="toggle(this)">
			<div style="display:none;">%s</div>
		</td>
		%s</tr>""" % (len(rows), self.nct, self.nct, len(rows), self.eligibility_formatted, rows[0])
		
		rows.pop(0)
		for row in rows:
			html += "<tr>%s</tr>" % row
		
		return html
	
	
	# extract single criteria from plain text eligibility criteria
	def process_eligibility_from_text(self):
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
		Don't forget to MANUALLY COMMIT at one point!
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
		
		if Study.sqlite_handle.execute(sql, params):
			Study.sqlite_must_commit = True
			self.hydrated = True
			return True
		
		return False
	
	
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
		data = Study.sqlite_handle.executeOne(sql, (self.nct,))
		
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
			
			self.hydrated = True
			
			# populate parsed eligibility criteria
			self.criteria = StudyEligibility.load_for_study(self)
	
	
	@classmethod
	def sqlite_commit_if_needed(cls):
		if cls.sqlite_must_commit:
			cls.sqlite_handle.commit()
			cls.sqlite_must_commit = False
	
	
	@classmethod
	def setup_tables(cls):
		if cls.sqlite_handle is None:
			cls.sqlite_handle = SQLite.get('storage.db')
		
		cls.sqlite_handle.create('studies', '''(
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
		StudyEligibility.ctakes = setting




# Study eligibility criteria management
class StudyEligibility (object):
	""" Holds one part of a study's eligibility criteria.
	Studies can have a lot of them.
	"""
	
	ctakes = {}
	
	
	def __init__(self, study):
		self.id = None
		self.hydrated = False
		self.study = study
		self.updated = None
		self.is_inclusion = False
		self.text = None
		self.snomed = []
		self.cui = []
		self.did_process = False
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
		for rslt in Study.sqlite_handle.execute(sql, (study.nct,)):
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
		self.snomed = data[5].split('|') if data[5] else []
		self.cui = data[6].split('|') if data[6] else []
		self.did_process = (1 == data[7])
	
	
	def codify(self):
		""" Three stages:
		      1. Reads the codes from SQLite, if they are there
		      2. Reads and stores the codes from the cTakes output dir, if they
		         are there
		      3. Writes the criteria to the cTakes input directory
		"""
		if self.did_process:
			return
		
		# 1. no codes and not hydrated, fetch from SQLite
		if not self.hydrated:
			raise Exception('must hydrate first (not yet implemented)')
		
		# 2. not there, look in cTakes OUTPUT directory
		ct = StudyEligibility.ctakes
		if ct['OUTPUT'] and os.path.exists(ct['OUTPUT']):
			outfile = os.path.join(ct['OUTPUT'], '%d.txt.xmi' % self.id)
			if os.path.exists(outfile):
				root = parse(outfile).documentElement
				code_nodes = root.getElementsByTagName('refsem:UmlsConcept')
				
				# pluck apart the codes
				if len(code_nodes) > 0:
					cuis = []
					snomeds = []
					for node in code_nodes:
						#print node.toxml()
						
						# extract SNOMED code
						if 'codingScheme' in node.attributes.keys() \
							and 'code' in node.attributes.keys() \
							and 'SNOMED' == node.attributes['codingScheme'].value:
							snomeds.append(node.attributes['code'].value)
						
						# extract UMLS CUI
						if 'cui' in node.attributes.keys():
							cuis.append(node.attributes['cui'].value)
					
					self.snomed = list(set(snomeds))
					self.cui = list(set(cuis))
					
				# mark as processed, store to SQLite and remove the files
				self.did_process = True
				if self.store():
					os.remove(outfile)
					infile = os.path.join(ct['INPUT'], '%d.txt' % self.id)
					if os.path.exists(infile):
						os.remove(infile)
				
				self.waiting_for_ctakes = False
				return
		
		# 3. not yet processed, put it there and wait for cTakes to process it
		if ct['INPUT'] and os.path.exists(ct['INPUT']):
			infile = os.path.join(ct['INPUT'], '%d.txt' % self.id)
			if not os.path.exists(infile):
				handle = codecs.open(infile, 'w', 'utf-8')
				handle.write(self.text)
				handle.close()
			self.waiting_for_ctakes = True
	
	
	def store(self):
		""" Stores the receiver's data to SQLite.
		You must MANUALLY COMMIT!
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
			self.id = Study.sqlite_handle.executeInsert(sql, params)
		
		# update the remaining stuff
		sql = '''UPDATE criteria SET
			updated = datetime(), is_inclusion = ?, text = ?, snomed = ?, cui = ?, did_process = ?
			WHERE criterium_id = ?'''
		params = (
			1 if self.is_inclusion else 0,
			self.text,
			'|'.join(self.snomed),
			'|'.join(self.cui),
			1 if self.did_process else 0,
			self.id
		)
		
		if Study.sqlite_handle.execute(sql, params):
			Study.sqlite_must_commit = True
			self.hydrated = True
			return True
		
		return False
	
	
	@classmethod
	def setup_tables(cls):
		Study.sqlite_handle.create('criteria', '''(
			criterium_id INTEGER PRIMARY KEY AUTOINCREMENT,
			study TEXT,
			updated TIMESTAMP,
			is_inclusion INTEGER,
			text TEXT,
			snomed TEXT,
			cui TEXT,
			did_process INTEGER DEFAULT 0
		)''')

