try:
    import json
except ImportError:
    import simplejson as json
import urllib2
import geohash # https://code.google.com/p/python-geohash/
from dbschema import Geo, sql_db

class RevGeo(object):
    def __init__(self, conf, host='localhost', port=8081):
        print conf
        self.enabled = conf.get('enabled', False)
        self.host = host
        self.port = port
        self.hashlen = conf.get('ghashlen', 5)

    def rev(self, lat, lon, api='geonames'):
        if not self.enabled:
            return None

        lat = float(lat)
        lon = float(lon)


        ''' Look up the `ghash' geohash; if found, return the cached
            content, else perform lookup and store in cache. '''

        ghash = geohash.encode(lat, lon)[:self.hashlen]
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
        data = func(lat, lon)
        if data is None or type(data) is not dict:
            return None

        ''' Store data in cache '''

        data['src'] = src
        data['ghash'] = ghash
        try:
            g = Geo(**data)
            g.save()
        except Exception, e:
            logging.warn("Cannot store GEO in DB: %s" % (str(e)))

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
            url = 'http://maps.googleapis.com/maps/api/geocode/json' + \
                    '?latlng=%s,%s&sensor=false' % (lat, lon)
            google_data = json.load(urllib2.urlopen(url))

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
