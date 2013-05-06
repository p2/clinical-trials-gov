#!/usr/bin/python
#
#  Run a local server


import os
import wsgi
import logging

from ClinicalTrials.study import Study
from ClinicalTrials.umls import UMLS

# prepare a run directory (for now it's always the same)
run_dir = "run-server"
if not os.path.exists(run_dir):
	os.mkdir(run_dir)
	os.mkdir(os.path.join(run_dir, 'ctakes_input'))
	os.mkdir(os.path.join(run_dir, 'ctakes_output'))

# setup
db_path = os.path.join(run_dir, 'storage.db')
Study.setup_tables(db_path)
Study.setup_ctakes({'root': run_dir, 'cleanup': False})
UMLS.import_snomed_if_necessary()


# start the server
if wsgi.DEBUG:
	logging.basicConfig(level=logging.DEBUG)
	wsgi.app.run(host='0.0.0.0', port=8008, reloader=True)
else:
	logging.basicConfig(level=logging.WARNING)
	wsgi.app.run(host='0.0.0.0', port=8008)
