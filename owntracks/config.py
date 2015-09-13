#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import os
from ConfigParser import RawConfigParser, NoOptionError
import codecs
import ast
import sys
import logging

class Config(RawConfigParser):
    def __init__(self, configuration_file):
        self.configfile = configuration_file
        self.scriptname = os.path.splitext(os.path.basename(sys.argv[0]))[0]

        self.topicparts = 3     # owntracks/gw/XX
        self.o2smonitor = None

        # [defaults]
        self.logfile    = os.getenv(self.scriptname.upper() + 'LOG', self.scriptname + '.log')
        self.loglevel   = 'INFO'
        self.logformat  = '%(asctime)-15s %(levelname)-5s [%(module)s] %(message)s'
        self.logconfig  = 'logging.conf'


        # [database]
        self.dbengine   = 'mysql'
        self.dbname     = 'owntracks'
        self.dbuser     = None
        self.dbpasswd   = None
        self.dbhost     = 'localhost'
        self.dbport     = 3306
        self.dbpath     = '/tmp/owntracks.db'


        RawConfigParser.__init__(self)
        try:
            f = codecs.open(configuration_file, 'r', encoding='utf-8')
            self.readfp(f)
            f.close()
        except:
            print "Cannot open configuration file ", configuration_file
            sys.exit(2)

        self.__dict__.update(self.config('defaults'))
        self.__dict__.update(self.config('database'))

        self.loglevelnumber = getattr(logging, self.loglevel.upper())
        self.o2smonitor     = self.g('features', 'o2smonitor')

    def g(self, section, key, default=None):
        try:
            val = self.get(section, key)
            return ast.literal_eval(val)
        except NoOptionError:
            return default
        except ValueError:   # e.g. %(xxx)s in string
            return val
        except:
            raise
            return val

    def config(self, section):
        d = {}
        if self.has_section(section):
            for key in self.options(section):
                d[key] = self.g(section, key)

        return d

