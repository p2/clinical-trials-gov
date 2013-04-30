#!/usr/bin/env python
#
#	Representing a ClinicalTrials.gov study
#
#	2012-12-13	Created by Pascal Pfiffner
#

import datetime
import dateutil.parser
import os
import logging
import codecs
from xml.dom.minidom import parse

import requests
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.WARNING)

from dbobject import DBObject
from nlp import split_inclusion_exclusion
from umls import UMLS, SNOMED
from paper import Paper


class Study (DBObject):
	""" Describes a study found on ClinicalTrials.gov.
	"""
	
	ctakes = {}
	
	def __init__(self, nct=0):
		super(Study, self).__init__()
		self.nct = nct
		self.papers = None
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
		
		self.waiting_for_ctakes_pmc = False
	
	
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
			
			t_inc = "\n\t".join(inc)
			t_exc = "\n\t".join(exc)
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
		snomed = SNOMED()
		is_first = True
		for crit in self.criteria:
			css_class = '' if is_first else 'crit_first'
			in_ex = 'in' if crit.is_inclusion else 'ex'
			
			# this criterium has been codified
			if len(crit.snomed) > 0:
				c_html = """<td class="%s" rowspan="%d">%s</td>
				<td class="%s" rowspan="%d">%s</td>""" % (css_class, len(crit.snomed), crit.text, css_class, len(crit.snomed), in_ex)
				
				for sno in crit.snomed:
					rows.append(c_html + """<td class="%s">%s</td>
						<td class="%s">%s</td>""" % (css_class, sno, css_class, snomed.lookup_code_meaning(sno)))
					if len(c_html) > 0:
						c_html = ''
					css_class = ''
			
			# no codes for this criterium
			else:
				rows.append("""<td class="%s">%s</td>
					<td class="%s">%s</td>
					<td class="%s"></td>""" % (css_class, crit.text, css_class, in_ex, css_class))
			
			is_first = False
		
		if len(rows) < 1:
			return ''
		
		# compose HTML
		html = """<tr class="trial_first">
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
		if self.criteria is not None:
			for criterium in self.criteria:
				criterium.codify()
	
	
	def waiting_for_ctakes(self):
		""" Returns True if any of our criteria needs to run through cTakes.
		"""
		if self.waiting_for_ctakes_pmc:
			return True
		
		if self.criteria and len(self.criteria) > 0:
			for criterium in self.criteria:
				if criterium.waiting_for_ctakes:
					return True
		
		return False
	
	
	# -------------------------------------------------------------------------- PubMed
	def run_pmc(self, run_dir):
		""" Finds, downloads, extracts and parses PMC-indexed publications for
		the trial. """
		self.find_pmc_packages()
		self.download_pmc_packages(run_dir)
		self.parse_pmc_packages(run_dir)
	
	
	def find_pmc_packages(self):
		""" Determine whether there was a PMC-indexed publication for the trial.
		"""
		if self.nct is None:
			logging.warning("Need an NCT before trying to find publications")
			return
		
		# find paper details
		self.papers = Paper.find_by_nct(self.nct)
		for paper in self.papers:
			paper.fetch_pmc_ids()
	
	
	def download_pmc_packages(self, run_dir):
		""" Downloads the PubMed Central packages for our papers. """
		
		if self.papers is not None:
			for paper in self.papers:
				paper.download_pmc_packages(run_dir)
	
	
	def parse_pmc_packages(self, run_dir):
		""" Looks for downloaded packages in the given run directory and
		extracts the paper text from the XML in the .nxml file.
		"""
		if self.papers is None:
			return
		
		if not os.path.exists(run_dir):
			raise Exception("The run directory %s doesn't exist" % run_dir)
		
		ct_in_dir = os.path.join(Study.ctakes.get('root', run_dir), 'ctakes_input')
		for paper in self.papers:
			paper.parse_pmc_packages(run_dir, ct_in_dir)
			
			# also dump CT criteria if the paper has methods
			if paper.has_methods:
				plaintextpath = os.path.join(ct_in_dir, "%s-%s-CT.txt" % (self.nct, paper.pmid))
				with codecs.open(plaintextpath, 'w', 'utf-8') as handle:
					handle.write(self.eligibility_formatted)
				
				self.waiting_for_ctakes_pmc = True
	
	
	
	# -------------------------------------------------------------------------- Database Storage
	
	def should_insert(self):
		""" We use REPLACE INTO, so we always update. """
		return True
	
	def should_update(self):
		return False
	
	def will_insert(self):
		if self.nct is None:
			raise Exception('NCT is not set')
	
	def insert_tuple(self):
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
		
		return sql, params
	
	
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
		data = DBObject.sqlite_select_one(sql, (self.nct,))
		
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
	
	
	# -------------------------------------------------------------------------- Class Methods
	table_name = 'studies'
	
	@classmethod
	def table_structure(cls):
		return '''(
			nct UNIQUE,
			updated TIMESTAMP,
			elig_gender INTEGER,
			elig_min_age INTEGER,
			elig_max_age INTEGER,
			elig_population TEXT,
			elig_sampling TEXT,
			elig_accept_healthy INTEGER DEFAULT 0,
			elig_criteria TEXT
		)'''
	
	
	@classmethod
	def setup_ctakes(cls, setting):
		cls.ctakes = setting
	
	
	# -------------------------------------------------------------------------- Utilities
	def __unicode__(self):
		return '<study.Study %s>' % (self.nct)
	
	def __str__(self):
		return unicode(self).encode('utf-8')
	
	def __repr__(self):
		return str(self)
	



# Study eligibility criteria management
class StudyEligibility (DBObject):
	""" Holds one part of a study's eligibility criteria.
	Studies can have a lot of them.
	"""
	
	def __init__(self, study):
		super(StudyEligibility, self).__init__()
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
		for rslt in cls.sqlite_select(sql, (study.nct,)):
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
	
	
	# -------------------------------------------------------------------------- Codification
	def read_ctakes_output(self):
		""" Reads and stores the codes from the cTakes output dir, if they
		are there. """
		
		ct = Study.ctakes
		if ct is None:
			return False
		
		# is there cTAKES output?
		ct_out = os.path.join(ct.get('root', '.'), 'ctakes_output')
		if not os.path.exists(ct_out):
			logging.error("The output directory for cTAKES at %s does not exist" % ct_out)
			return False
		
		outfile = os.path.join(ct_out, '%d.txt.xmi' % self.id)
		if not os.path.exists(outfile):
			return False
		
		# parse XMI file
		root = parse(outfile).documentElement
		
		# pluck apart the SNOMED codes
		code_nodes = root.getElementsByTagName('refsem:UmlsConcept')
		if len(code_nodes) > 0:
			cuis = []
			snomeds = []
			for node in code_nodes:
				#print node.toprettyxml()
				
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
			
		# mark as processed
		self.did_process = True
		
		# store to SQLite and remove the files if desired
		cleanup = ct['cleanup'] if 'cleanup' in ct else False
		if self.store() and cleanup:
			os.remove(outfile)
			
			ct_in = os.path.join(ct.get('root', '.'), 'ctakes_input')
			infile = os.path.join(ct_in, '%d.txt' % self.id)
			if os.path.exists(infile):
				os.remove(infile)
		
		self.waiting_for_ctakes = False
		return True
	
	def codify(self):
		""" Three stages:
		      1. Reads the codes from SQLite, if they are there
		      2. Reads and stores the codes from the cTakes output dir, if they
		         are there
		      3. Writes the criteria to the cTakes input directory and sets the
		         "waiting_for_ctakes" flag
		"""
		if self.did_process:
			return
		
		# 1. no codes and not hydrated, fetch from SQLite
		if not self.hydrated:
			raise Exception('must hydrate first (not yet implemented)')
		
		# 2. not there, look in cTakes output directory
		if self.read_ctakes_output():
			return
		
		# 3. not yet processed, put it there and wait for cTakes to process it
		ct = Study.ctakes
		if ct is None:
			logging.error("cTAKES has not been configured")
			return
		
		ct_in = os.path.join(ct.get('root', '.'), 'ctakes_input')
		if ct_in and os.path.exists(ct_in):
			infile = os.path.join(ct_in, '%d.txt' % self.id)
			if not os.path.exists(infile):
				with codecs.open(infile, 'w', 'utf-8') as handle:
					handle.write(self.text)
				
				self.waiting_for_ctakes = True
			return
		
		# still here - not properly set up
		if 'input' not in ct:
			logging.error("The input directory for cTAKES has not been configured")
		elif not os.path.exists(ct_in):
			logging.error("The input directory for cTAKES at %s does not exist" % ct_in)
		elif 'output' not in ct:
			logging.error("The output directory for cTAKES has not been configured")
	
	
	def should_insert(self):
		return self.id is None
	
	def will_insert(self):
		if self.study is None or self.study.nct is None:
			raise Exception('Study NCT is not set')
	
	def insert_tuple(self):
		sql = '''INSERT OR IGNORE INTO criteria
				(criterium_id, study) VALUES (?, ?)'''
		params = (
			self.id,
			self.study.nct
		)
		
		return sql, params
	
	def update_tuple(self):
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
		
		return sql, params
	
	
	# -------------------------------------------------------------------------- Class Methods
	table_name = 'criteria'
	
	@classmethod
	def table_structure(cls):
		return '''(
			criterium_id INTEGER PRIMARY KEY AUTOINCREMENT,
			study TEXT,
			updated TIMESTAMP,
			is_inclusion INTEGER,
			text TEXT,
			snomed TEXT,
			cui TEXT,
			did_process INTEGER DEFAULT 0
		)'''
	
	
	# -------------------------------------------------------------------------- Utilities
	def __unicode__(self):
		return '<study.StudyEligibility %s (%s)>' % (self.nct, 'inclusion' if self.is_inclusion else 'exclusion')
	
	def __str__(self):
		return unicode(self).encode('utf-8')
	
	def __repr__(self):
		return str(self)


# init tables
Study.setup_tables()
StudyEligibility.setup_tables()

