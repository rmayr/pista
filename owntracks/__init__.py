# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'

import os
import config
import logging

cf = config.Config(os.getenv('O2SCONFIG', 'o2s.conf'))

logging.basicConfig(filename=cf.logfile, level=cf.loglevelnumber, format=cf.logformat)
logging.info("Starting %s" % __name__)
logging.info("INFO MODE")
logging.debug("DEBUG MODE")
