#!/usr/bin/python
# Setup for owntracks-pista by Rene Mayrhofer

#from distutils.core import setup
from setuptools import setup
import os
import re
import sys

# the package name
SCRIPT = 'pista.py'
VERSION = '0.20150317'

keys = ('__license__', '__author__')
options = dict()
sc = open(SCRIPT)
sclines = sc.readlines()
for line in sclines:
    if not line.strip(): # skip empty or space padded lines
	continue
    if re.compile('^#').search(line) is not None: # skip commented lines
	continue
      
    kvp = line.strip().split('=')
    if kvp[0].strip() in keys:
	options[kvp[0].strip(' \'')] = kvp[1].strip(' \'')

# These metadata fields are simply taken from the script
LICENSE = options['__license__']

# Extract name and e-mail ("Firstname Lastname <mail@example.org>")
AUTHOR, EMAIL = re.match(r'(.*) <(.*)>', options['__author__']).groups()

setup(name=SCRIPT,
      version=VERSION,
      author=AUTHOR,
      author_email=EMAIL,
      license=LICENSE,

      scripts= [SCRIPT, 'o2s.py', 'alarmhelper.py'],
      packages = ['owntracks', 'owntracks/auth'],
#      data_files = [('/srv/owntracks/pista', ['tools', 'static', 'views']),
#                    ],
#      test_suite = '',

      description=  'owntracks pista',
  )
