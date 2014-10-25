#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ConfigParser import RawConfigParser, NoOptionError
import codecs
import ast
import sys

class conf(RawConfigParser):
    def __init__(self, configuration_file):
        RawConfigParser.__init__(self)
        try:
            f = codecs.open(configuration_file, 'r', encoding='utf-8')
            self.readfp(f)
            f.close()
        except:
            print "Cannot open configuration file ", configuration_file
            sys.exit(2)

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

