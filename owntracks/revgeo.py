__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import owntracks
import logging
try:
    import json
except ImportError:
    import simplejson as json
import urllib2
import geohash # https://code.google.com/p/python-geohash/
from owntracks.dbschema import db, Geo

log = logging.getLogger(__name__)

class RevGeo(object):
    def __init__(self, conf, storage=True, host='localhost', port=8081):
        self.enabled = conf.get('enabled', False)
        self.host = host
        self.port = port
        self.hashlen = conf.get('ghashlen', 5)
        self.storage = storage
        self.region_bias = conf.get('region_bias', 'de')

    def rev(self, lat, lon, api='geonames'):
        if not self.enabled:
            return None

        lat = float(lat)
        lon = float(lon)


        ''' Look up the `ghash' geohash; if found, return the cached
            content, else perform lookup and store in cache. '''

        ghash = geohash.encode(lat, lon)[:self.hashlen]
        if self.storage:
            try:
                g = Geo.get(Geo.ghash == ghash)
                return dict(ghash=ghash, cc=g.cc, addr=g.addr, cached=1)
            except Geo.DoesNotExist:
                pass
            except Exception, e:
                raise

        methods = {
            'geonames' : (1, self._geoname),
            'google'   : (2, self._google),
        }

        if api not in methods:
            return None


        src = methods[api][0]
        func = methods[api][1]
        # print "FIXME: rev lookup src={0}, lat={1}, lon={2} method={3}".format(src, lat, lon, api)

        data = func(lat, lon)
        if data is None or type(data) is not dict:
            return None

        ''' Store data in cache '''

        data['src'] = src
        data['ghash'] = ghash
        if self.storage:
            try:
                g = Geo(**data)
                g.save()
            except Exception, e:
                log.warn("Cannot store GEO in DB: %s" % (str(e)))

        return dict(ghash=ghash, cc=data['cc'], addr=data['addr'], cached=0)

    def _geoname(self, lat, lon):
        try:
            r = urllib2.urlopen('http://%s:%s/%s,%s' % (self.host, self.port, lat, lon))
            s = r.read().decode('utf-8') 
            
            (geoname, km, cc, addr) = s.split('|')
            revgeo = {
                'geoname' : geoname,
                'km' : km,
                'cc' : cc,
                'addr' : addr,
            }
            
            return revgeo
        except Exception, e:
            raise
            print "\t%s" % str(e)

    def _google(self, lat, lon):

        try:
            # https://developers.google.com/maps/documentation/geocoding/
            maplang = self.region_bias
            url = 'http://maps.googleapis.com/maps/api/geocode/json' + \
                    '?latlng=%s,%s&sensor=false&language=%s&region=%s' % (lat, lon, maplang, self.region_bias)
            google_data = json.load(urllib2.urlopen(url, timeout=5))

            revgeo = { }
            if 'status' in google_data and google_data['status'] != 'OK':
                # FIXME: log status
                return None

            revgeo['addr'] = google_data['results'][0]['formatted_address']
            for el in google_data['results'][0]['address_components']:
                if 'country' in el['types']:
                    revgeo['cc'] =  el['short_name']
            return revgeo
        except:
            return None
