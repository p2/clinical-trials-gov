#!/usr/bin/env python
#
#	Simplifying SQLite access
#
#	2012-12-14	Created by Pascal Pfiffner
#


import sqlite3


SQLITE_INSTANCES = {}


class SQLite (object):
	""" SQLite access
	"""
	
	@classmethod
	def get(cls, database=None):
		""" Use this to get SQLite instances for a given database. Avoids
		creating multiple instances for the same database.
		"""
		if database is None:
			raise Exception('No database provided')
		
		global SQLITE_INSTANCES
		if database not in SQLITE_INSTANCES:
			sql = SQLite(database)
			SQLITE_INSTANCES[database] = sql
		
		return SQLITE_INSTANCES[database]
	
	
	def __init__(self, database=None):
		if database is None:
			raise Exception('No database provided')
		
		self.database = database
		self.handle = None
		self.cursor = None

	
	def executeInsert(self, sql, params=()):
		""" Executes an SQL command (should be INSERT OR REPLACE) and returns
		the last row id, 0 on failure.
		"""
		if not sql or len(sql) < 1:
			raise Exception('No SQL to execute')
		if not self.cursor:
			self.connect()
		
		if self.cursor.execute(sql, params):
			return self.cursor.lastrowid if self.cursor.lastrowid else 0
		
		return 0
	
		
	def execute(self, sql, params=()):
		""" Executes an SQL command and returns the cursor.execute, which can
		be used as an iterator.
		Supply the params as tuple, i.e. (param,) and (param1,param2,...)
		"""
		if not sql or len(sql) < 1:
			raise Exception('no SQL to execute')
		if not self.cursor:
			self.connect()
		
		return self.cursor.execute(sql, params)


	def executeOne(self, sql, params):
		""" Returns the first row returned by executing the command
		"""
		self.execute(sql, params)
		return self.cursor.fetchone()


	def create(self, table_name, table_structure):
		""" Executes a CREATE TABLE IF NOT EXISTS query with the given structure.
		Input is NOT sanitized, watch it!
		"""
		create_query = 'CREATE TABLE IF NOT EXISTS %s %s' % (table_name, table_structure)
		self.execute(create_query)


	def commit(self):
		self.handle.commit()


	def connect(self):
		if self.cursor is not None:
			return
		
		self.handle = sqlite3.connect(self.database)
		self.cursor = self.handle.cursor()


	def close(self):
		if self.cursor is None:
			return
		
		self.handle.close()
		self.cursor = None
		self.handle = None


# singleton init whack-a-hack
#SQLite = _SQLite()
#del _SQLite
