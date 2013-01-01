#!/usr/bin/env python
#
#	utilities to handle UMLS
#
#	2013-01-01	Created by Pascal Pfiffner
#


import csv
import sys
import os.path

from sqlite import SQLite


class UMLS (object):
	""" Handling UMLS and SNOMED
	"""
	
	sqlite_handle = None
	umls_file = None
	
	
	@classmethod
	def lookup_snomed(cls, snomed_id):
		""" Returns the term for the given SNOMED code.
		"""
		if not snomed_id:
			raise Exception('No SNOMED code provided')
		
		sql = 'SELECT term FROM snomed WHERE concept_id = ?'
		res = cls.sqlite_handle.executeOne(sql, (snomed_id,))
		if res:
			return res[0]
		
		return ''
	
	
	@classmethod
	def import_snomed_from_csv(cls):
		""" Read SNOMED CT from tab-separated file and create an SQLite database
		from it.
		"""
		
		# no need to import?
		num_query = 'SELECT COUNT(*) FROM snomed'
		num_existing = UMLS.sqlite_handle.executeOne(num_query, ())[0]
		if num_existing > 0:
			return
		
		print 'Importing SNOMED concepts into umls.db...'
		
		# not yet imported, parse tab-separated file and import
		if cls.umls_file is None:
			raise Exception('No raw SNOMED file given, setup first!')
		if not os.path.exists(cls.umls_file):
			raise Exception('The SNOMED file at %s does not exist', cls.umls_file)
		
		with open(cls.umls_file, 'rb') as csv_handle:
			reader = unicode_csv_reader(csv_handle, dialect='excel-tab')
			i = 0
			try:
				for row in reader:
					if i > 0:
						
						# execute SQL (we just ignore duplicates)
						sql = '''INSERT OR IGNORE INTO snomed
							(concept_id, lang, term)
							VALUES
							(?, ?, ?)'''
						params = (int(row[4]), row[5], row[7])
						try:
							cls.sqlite_handle.execute(sql, params)
						except Exception as e:
							sys.exit(u'Cannot insert %s: %s' % (params, e))
					i += 1
				
				# commit to file
				cls.sqlite_handle.commit()
			
			except csv.Error as e:
				sys.exit('CSV error on line %d: %s' % (reader.line_num, e))

		print '%d concepts parsed' % (i-1)


	@classmethod
	def setup_tables(cls):
		""" Creates the SQLite tables and imports SNOMED from flat files, if
		not already done
		"""
		if cls.sqlite_handle is None:
			cls.sqlite_handle = SQLite.get('umls.db')
		
		cls.sqlite_handle.create('snomed', '''(
				concept_id INTEGER PRIMARY KEY,
				lang TEXT,
				term TEXT
			)''')
		
		cls.import_snomed_from_csv()
	
	
	@classmethod
	def setup_umls(cls, umls_file):
		cls.umls_file = umls_file
		

# the standard Python CSV reader can't do unicode, here's the workaround
def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
	csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
	for row in csv_reader:
		yield [unicode(cell, 'utf-8') for cell in row]

