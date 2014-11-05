# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'

import os
import config

cf = config.Config(os.getenv('O2SCONFIG', 'o2s.conf'))
