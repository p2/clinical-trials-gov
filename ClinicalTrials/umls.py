#!/usr/bin/env python
#
#	utilities to handle UMLS
#
#	2013-01-01	Created by Pascal Pfiffner
#


import csv
import sys
import os.path
import logging

from sqlite import SQLite


class UMLS(object):
	""" A class for importing UMLS terminologies into an SQLite database.
	
	For now only handles SNOMED CSV import.
	"""
	
	sqlite_handle = None
	umls_file = None
	
	
	@classmethod
	def import_snomed_if_necessary(cls):
		""" Read SNOMED CT from tab-separated file and create an SQLite database.
		"""
		
		cls.setup_snomed_tables()
		map = {
			'descriptions': 'snomed_desc.csv',
			'relationships': 'snomed_rel.csv'
		}
		
		# need to import?
		for table, filename in map.iteritems():
			num_query = 'SELECT COUNT(*) FROM %s' % table
			num_existing = UMLS.sqlite_handle.executeOne(num_query, ())[0]
			if num_existing > 0:
				continue
			
			snomed_file = os.path.join('databases', filename)
			if not os.path.exists(snomed_file):
				logging.warning("Need to import SNOMED, but the file %s is not present" % filename)
				continue
			
			cls.import_snomed_csv_into_table(snomed_file, table)
	
	
	@classmethod
	def import_snomed_csv_into_table(cls, snomed_file, table_name):
		logging.debug('..>  Importing SNOMED %s into snomed.db...' % table_name)
		
		# not yet imported, parse tab-separated file and import
		with open(snomed_file, 'rb') as csv_handle:
			cls.sqlite_handle.isolation_level = 'EXCLUSIVE'
			sql = cls.insert_query_for('snomed', table_name)
			reader = unicode_csv_reader(csv_handle, dialect='excel-tab')
			i = 0
			try:
				for row in reader:
					if i > 0:			# first row is the header row
						
						# execute SQL (we just ignore duplicates)
						params = cls.insert_tuple_from_csv_row_for('snomed', table_name, row)
						try:
							cls.sqlite_handle.execute(sql, params)
						except Exception as e:
							sys.exit(u'Cannot insert %s: %s' % (params, e))
					i += 1
				
				# commit to file
				cls.sqlite_handle.commit()
				cls.after_import('snomed', table_name)
				cls.sqlite_handle.isolation_level = None
			
			except csv.Error as e:
				sys.exit('CSV error on line %d: %s' % (reader.line_num, e))

		logging.debug('..>  %d concepts parsed' % (i-1))


	@classmethod
	def setup_snomed_tables(cls):
		""" Creates the SQLite tables we need, not the tables we deserve.
		"""
		if cls.sqlite_handle is None:
			cls.sqlite_handle = SQLite.get('databases/snomed.db')
		
		# descriptions
		cls.sqlite_handle.create('descriptions', '''(
				concept_id INTEGER PRIMARY KEY,
				lang TEXT,
				term TEXT,
				active INT
			)''')
		
		# relationships
		cls.sqlite_handle.create('relationships', '''(
				relationship_id INTEGER PRIMARY KEY,
				source_id INT,
				destination_id INT,
				rel_type INT,
				rel_text VARCHAR,
				active INT
			)''')
		cls.sqlite_handle.execute("CREATE INDEX IF NOT EXISTS source_index ON relationships (source_id)")
		cls.sqlite_handle.execute("CREATE INDEX IF NOT EXISTS destination_index ON relationships (destination_id)")
		cls.sqlite_handle.execute("CREATE INDEX IF NOT EXISTS rel_type_index ON relationships (rel_type)")
		cls.sqlite_handle.execute("CREATE INDEX IF NOT EXISTS rel_text_index ON relationships (rel_text)")
		
	
	@classmethod
	def insert_query_for(cls, db_name, table_name):
		""" Returns the insert query needed for the given table
		"""
		if 'snomed' == db_name:
			if 'descriptions' == table_name:
				return '''INSERT OR IGNORE INTO descriptions
							(concept_id, lang, term, active)
							VALUES
							(?, ?, ?, ?)'''
			if 'relationships' == table_name:
				return '''INSERT OR IGNORE INTO relationships
							(relationship_id, source_id, destination_id, rel_type, active)
							VALUES
							(?, ?, ?, ?, ?)'''
		return None
	
	
	@classmethod
	def insert_tuple_from_csv_row_for(cls, db_name, table_name, row):
		if 'snomed' == db_name:
			if 'descriptions' == table_name:
				return (int(row[4]), row[5], row[7], int(row[2]))
			if 'relationships' == table_name:
				return (int(row[0]), int(row[4]), int(row[5]), int(row[7]), int(row[2]))
		return None
	
	
	@classmethod
	def after_import(cls, db_name, table_name):
		""" Allows us to set hooks after tables have been imported
		"""
		if 'snomed' == db_name:
			if 'relationships' == table_name:
				cls.sqlite_handle.execute('''
					UPDATE relationships SET rel_text = 'isa' WHERE rel_type = 116680003
					''')
				cls.sqlite_handle.execute('''
					UPDATE relationships SET rel_text = 'finding_site' WHERE rel_type = 363698007
					''')


class SNOMED(object):
	""" SNOMED lookup """
	
	def __init__(self):
		self.sqlite = SQLite.get('databases/snomed.db')
	
	def lookup_code_meaning(self, snomed_id):
		if not snomed_id:
			raise Exception('No SNOMED code provided')
		
		sql = 'SELECT term FROM descriptions WHERE concept_id = ?'
		res = self.sqlite.executeOne(sql, (snomed_id,))
		if res:
			return res[0]
		return ''


# the standard Python CSV reader can't do unicode, here's the workaround
def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
	csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
	for row in csv_reader:
		yield [unicode(cell, 'utf-8') for cell in row]

