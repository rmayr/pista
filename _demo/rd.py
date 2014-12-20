#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import csv
import sys
import string

ins = {
    'owntracks-AK-2014-11-08-2014-11-08.csv' : 'dK',
    'owntracks-BB-2014-10-06-2014-10-06.csv' : 'dB',
    'owntracks-HE-2014-11-09-2014-11-11.csv' : 'dH',
    'owntracks-MV-2014-10-23-2014-10-25.csv' : 'dM',
    'owntracks-PN-2014-12-15-2014-12-15.csv' : 'dN',
    'owntracks-MV-2014-12-16-2014-12-16.csv' : 'dG'
}

t = string.Template("Loc('$tid', $lat, $lon, $alt, $vel, $cog, '$t', $dist, $trip),")

data = open("data.py", "w")
data.write("# created by rd.py\n")
data.write("from collections import namedtuple\n")
data.write("\n")
data.write("Loc = namedtuple('Loc', 'tid lat lon alt vel cog t dist trip')\n\n\n")

for el in ins:
    f = open(el, 'r')
    tid = ins[el]


    data.write("def _%s():\n    return [\n" % (tid))

    # "cc";"alt";"t";"cog";"lat";"tst";"lon";"vel";"ghash";"addr"
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        row['tid'] = tid
        s = t.substitute(**row)
        data.write("        %s\n" % s)

    f.close()

    data.write("    ]\n\n")

