#!/usr/bin/env python

import zipfile
import csv
import cdb
import sys

csv.field_size_limit(sys.maxsize)

if __name__ == '__main__':

    latlon = cdb.cdbmake('latlon.cdb', 'latlon.cdb.tmp')
    geonames = cdb.cdbmake('geonames.cdb', 'geonames.cdb.tmp')
    for fn in sys.argv[1:]:
        zf = zipfile.ZipFile(fn, 'r')
        for name in zf.namelist():
            if name == 'readme.txt':
                continue
            info = zf.getinfo(name)
            print "Reading ", name, " ... ", info.file_size
            f = zf.open(name, 'r')

            try:
                reader = csv.reader(f, delimiter="\t")
                for row in reader:
                    geonameid = row[0]
                    name  = row[1]
                    lat   = row[4]
                    lon   = row[5]
                    cl    = row[6]
                    cc    = row[8]
                    pop   = row[14]

                    if geonameid == '2823946':
                        continue

                    key = "%s,%s" % (lat, lon)
                    latlon.add(key, geonameid)

                    geonames.add(geonameid, "%s|%s" % (cc, name))
            except Exception, e:
                print str(e)
                continue

            zf.close()

    latlon.finish()
    geonames.finish()
