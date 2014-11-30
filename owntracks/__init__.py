# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import os
import config
import logging
import logging.config

cf = config.Config(os.getenv('O2SCONFIG', 'o2s.conf'))

logging.basicConfig(filename=cf.logfile, level=cf.loglevelnumber, format=cf.logformat)
logging.info("Starting %s" % __name__)
logging.info("INFO MODE")
logging.debug("DEBUG MODE")

# logging.config.fileConfig(cf.logconfig, disable_existing_loggers=False) #FIXME needs study!
