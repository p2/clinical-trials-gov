#!/usr/bin/python
#
#  Run a local server


import wsgi
import logging

from ClinicalTrials.study import Study
from ClinicalTrials.umls import UMLS

from settings import UMLS_FILE, CTAKES


# setup
Study.setup_ctakes(CTAKES)
Study.setup_tables()
UMLS.import_snomed_if_necessary()


# start the server
if wsgi.DEBUG:
	logging.basicConfig(level=logging.DEBUG)
	wsgi.app.run(host='0.0.0.0', port=8008, reloader=True)
else:
	logging.basicConfig(level=logging.WARNING)
	wsgi.app.run(host='0.0.0.0', port=8008)
