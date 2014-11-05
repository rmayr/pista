#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'

import sys
import logging
import bottle
from bottle import response, template, static_file, request
from bottle import auth_basic, error
import json
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
import os
import codecs
from datetime import datetime
from dateutil import tz
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.etree import ElementTree as ET
from owntracks.ElementTree_pretty import prettify
import time
from owntracks import cf
from owntracks.wredis import Wredis
import paho.mqtt.client as paho
from owntracks.dbschema import db, Geo, Location, Waypoint, User, Acl, JOIN_LEFT_OUTER, fn
from owntracks.auth import PistaAuth
from owntracks import haversine

LOGFORMAT  = '%(asctime)-15s %(levelname)-5s [%(module)s] %(message)s'
logging.basicConfig(filename="XXXX.log", level=logging.DEBUG, format=LOGFORMAT)
logging.info("Starting %s" % __name__)
logging.info("INFO MODE")
logging.debug("DEBUG MODE")

auth = PistaAuth()

POINT_KM = 20

app = application = bottle.Bottle()
bottle.SimpleTemplate.defaults['get_url'] = app.get_url

redis = Wredis(cf.config('redis'))

def notauth(reason):
    return bottle.HTTPResponse(status=403, body=reason)

def check_auth(username, password):
    return auth.check(username, password, apns_token=None)


def db_reconnect():
    # Attempt to connect if not already connected. For MySQL, take care of MySQL 2006
    try:
        db.connect()
    except Exception, e:
        logging.info("Cannot connect to database: %s" % (str(e)))

def track_length(track):
    ''' Run through the track, calculate distance in kilometers
        and return that. '''

    kilometers = 0.0
    n = 1
    for tp in track[0:-1]:
        distance = haversine.haversine(tp['lon'], tp['lat'], track[n]['lon'], track[n]['lat'])
        kilometers += distance
        n += 1

    return kilometers

def normalize_date(d):

    if d == 'NaN-NaN-NaN' or d == "" or d is None:
        d = time.strftime("%Y-%m-%d")
    return d

def getDBdata(usertid, from_date, to_date, spacing):

    track = []

    from_date = normalize_date(from_date)
    to_date   = normalize_date(to_date)

    to_date = "%s 23:59:59" % to_date
    print "FROM=%s, TO=%s" % (from_date, to_date)

    db_reconnect()

# select tst, lat, lon, l.ghash, addr from location l left join geo g on l.ghash = g.ghash where tid = 'B2';

    #query = Location.select().join(Geo, JOIN_LEFT_OUTER, on=Geo.ghash).where(
    #            (Location.username == username) &
    #            (Location.device == device) &
    #            (Location.tst.between(from_date, to_date))
    #            )
    query = (Location
                .select(Location, Geo.addr.alias('addr'))
                .join(Geo, JOIN_LEFT_OUTER, on=(Location.ghash == Geo.ghash)).
                where(
                    # (Location.username == username) &
                    # (Location.device == device) &
                    (Location.tid == usertid) &
                    (Location.tst.between(from_date, to_date))
                )
            )
    query = query.order_by(Location.tst.asc())
    for l in query.naive():

        dbid    = l.id
        lat     = float(l.lat)
        lon     = float(l.lon)
        dt      = l.tst

        # FIXME: add distance haversine to previous point
        # FIXME: check values (vel, dist, trip...

        try:
            tp = {
                'lat' : float(l.lat),
                'lon' : float(l.lon),
                'tst' : l.tst,
                't'   : l.t,
                'vel' : int(l.vel),
                'cog' : int(l.cog),
                'alt' : int(l.alt),
                'ghash' : l.ghash,
                'cc'  : l.cc,
                'addr' : l.addr,
            }

            track.append(tp)
        except:
            pass

    return track

def getDBwaypoints(usertid, lat_min, lat_max, lon_min, lon_max):

    waypoints = []

    # FIXME: this needs authorization

    lat_min = float(lat_min)
    lat_max = float(lat_max)
    lon_min = float(lon_min)
    lon_max = float(lon_max)

    db_reconnect()
    query = Waypoint.select().where(
                # FIXME (Waypoint.username == username) &
                # FIXME (Waypoint.device == device) &
                    (Waypoint.lat >= lat_min) &
                    (Waypoint.lat <= lat_max) &
                    (Waypoint.lon >= lon_min) &
                    (Waypoint.lon <= lon_max)
                )

    for q in query:

        if q.rad is None:
            continue

        wp = {
            'lat'  : float(q.lat),
            'lon'  : float(q.lon),
            'name' : q.waypoint,
            'rad'  : q.rad,
        }
        waypoints.append(wp)

    return waypoints

def getusertids(username):
    ''' username is probably a logged-in user. Obtain a list of TIDs
        that user is allowed to see '''

    # First, get a list of ACL topics the user is authorized for. If the
    # `username' is a superuser, add '#' to the subscription list, so
    # that paho matches that as true in any case. (Superusers possibly
    # don't have ACL entries in the database.)

    sublist = []

    superuser = False
    try:
        u = User.get(User.username == username)
        superuser = u.superuser
    except User.DoesNotExist:
        # logging.debug("User {0} does not exist".format(username))
        pass
    except Exception, e:
        raise

    if not superuser:
        query = (Acl.select(Acl). where(
                    (Acl.username == username)
                ))
        sublist = [ q.topic for q in query.naive() ]
    else:
        sublist.append('#')

    # Find distinct topic, tid combinations in Locations table and
    # let Paho check if subscription matches

    topiclist = []
    tidlist = []

    query = (Location.select(Location.tid, Location.topic)
                    .distinct()
                    .order_by(Location.tid)
                    )
    for q in query:
        for sub in sublist:
            if paho.topic_matches_sub(sub, q.topic):
                tidlist.append(q.tid)
                topiclist.append(q.topic)

    print "User {0} gets tidlist={1}".format(username, ",".join(tidlist))

    return tidlist


#-----------------

@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'

@app.route('/index')
@auth_basic(check_auth)
def index():
    return template('index', pistapages=cf.g('pista', 'pages'))

@app.route('/about')
def page_about():

    return template('about', pistapages=cf.g('pista', 'pages'))

@app.route('/console')
@auth_basic(check_auth)
def page_console():
    return template('console', pistapages=cf.g('pista', 'pages'))

@app.route('/map')
@auth_basic(check_auth)
def page_map():
    return template('map', pistapages=cf.g('pista', 'pages'))

@app.route('/hw')
@auth_basic(check_auth)
def page_hw():

    # FIXME: user auth

    device_list = []

    # Find all devices in Redis and extract their info into a list
    # of objects. Ensure values of hash keys are None if unset or
    # the template will bail out.

    for device in redis.keys("t:*"):
        data = redis.hgetall(device)
        tid     = data.get('tid', None)
        imei    = data.get('imei', None)
        version = data.get('version', None)
        tstamp  = data.get('tstamp', None)

        if tid is not None and imei is not None and version is not None and tstamp is not None:

            try:
                device_list.append({
                    'tid'       : tid,
                    'status'    : int(data.get('status', -1)),
                    'imei'      : imei,
                    'version'   : version,
                    'tstamp'    : tstamp,
                    'npubs'     : data.get('npubs', None),
                    'topic'     : device[2:],
                    })
            except:
                pass

    device_list.sort(key=lambda x: x['tid'], reverse=False)
    params = {
            'devices' : device_list,
            'pistapages' : cf.g('pista', 'pages'),
    }

    return template('hw', params)

@app.route('/status')
@auth_basic(check_auth)
def page_console():
    return template('status', pistapages=cf.g('pista', 'pages'))

@app.route('/table')
@auth_basic(check_auth)
def page_table():
    return template('table', pistapages=cf.g('pista', 'pages'))

@app.route('/tracks')
@auth_basic(check_auth)
def page_tracks():
    return template('tracks', pistapages=cf.g('pista', 'pages'))

@app.route('/hello')
def hello():
    data = {
        'name' : "JP Mens",
        'number' : 42,
    }
    return data

@app.route('/config.js')
@auth_basic(check_auth)
def config_js():
    ''' Produce a `config.js' from the [websocket] section of our config
        file. We have to muck about a bit to convert None etc. to JavaScript
        types ... '''

    newconf = cf.config('websocket')
    basic_auth = True
    if 'basic_auth' in newconf and newconf['basic_auth'] == False:
        basic_auth = False

    for key in newconf:
        if type(newconf[key]) == str:
            if newconf[key][0] != '"' and newconf[key][0] != '"':
                newconf[key] = "'" + newconf[key] + "'"
        if type(newconf[key]) == bool:
            newconf[key] = 'true' if newconf[key] else 'false';
        # print key, " = ", type(newconf[key]), " : ",  newconf[key]

    newconf['configfile'] = cf.configfile

    if basic_auth == True:
        u = request.auth[0]
        u = u.replace("'", "\\'")

        p = request.auth[1]
        p = p.replace("'", "\\'")

        newconf['username'] = "'{0}'".format(u)
        newconf['password'] = "'{0}'".format(p)

    response.content_type = 'text/javascript; charset: UTF-8'
    return template('config-js', newconf)

@app.route('/api/userlist')
@auth_basic(check_auth)
def users():
    ''' Get list of username - device pairs to populate a select box
        the id in that select will be set to username|device '''

    current_user = request.auth[0]

    allowed_tids = []

    db_reconnect()

    usertids = getusertids(current_user)

    for t in usertids:
        allowed_tids.append({
            'id' : t,
            'name' : t,
        })

    return dict(userlist=allowed_tids)


# ?usertid=XX&fromdate=2014-08-19&todate=2014-08-20&format=txt
@app.route('/api/download', method='GET')
@auth_basic(check_auth)
def get_download():
    mimetype = {
        'csv':  'text/csv',
        'txt':  'text/plain',
        'gpx':  'application/gpx+xml',
    }

    current_user = request.auth[0]

    usertid = request.params.get('usertid')
    from_date = request.params.get('fromdate')
    to_date = request.params.get('todate')
    fmt = request.params.get('format')

    from_date = normalize_date(from_date)
    to_date   = normalize_date(to_date)

    # before allowing download check for usertid auth
    usertids = getusertids(current_user)
    if usertid not in usertids:
        logging.warn("User {0} is not authorized to download data for tid={1}".format(current_user, usertid))
        return notauth(reason="Not authorized for this TID")

    if fmt not in mimetype:
        return { 'error' : "Unsupported download-type requested" }

    trackname = 'owntracks-%s-%s-%s' % (usertid, from_date, to_date)

    track = getDBdata(usertid, from_date, to_date, None)

    kilometers = track_length(track)

    sio = StringIO()
    s = codecs.getwriter('utf8')(sio)

    if fmt == 'txt':

        s.write("%-10s %-10s %s %s\n" % ("Latitude", "Longitude", "Timestamp (UTC)", "Location"))

        for tp in track:

            revgeo = tp.get('revgeo', "")

            s.write(u'%-10s %-10s %s %-14s %s\n' % \
                (tp.get('lat'),
                tp.get('lon'),
                tp.get('tst'),
                tp.get('addr', ""),
                revgeo))
        s.write("\nTrip: %.2f kilometers" % (kilometers))

    if fmt == 'csv':

        tp = track[0]
        title = ""
        for key in tp.keys():
            title = title + u'"%s";' % key

        s.write("%s\n" % title[0:-1])  # chomp last separator

        for tp in track:
            line = ""
            for key in tp:
                line = line + u'"%s";' % tp[key]

            s.write(u'%s\n' % line)

    if fmt == 'gpx':
        root = ET.Element('gpx')
        root.set('version', '1.0')
        root.set('creator', 'OwnTracks GPX Exporter')
        root.set('xmlns', "http://www.topografix.com/GPX/1/0")
        root.append(Comment('JP'))

        gpxtrack = Element('trk')
        track_name = SubElement(gpxtrack, 'name')
        track_name.text = trackname
        track_desc = SubElement(gpxtrack, 'desc')
        track_desc.text = "Trip: %.2f kilometers" % (kilometers)

        segment = Element('trkseg')
        gpxtrack.append(segment)

        trackpoints = []

        for tp in track:
            t = Element('trkpt')
            t.set('lat', str(tp['lat']))
            t.set('lon', str(tp['lon']))
            t_time = SubElement(t, 'time')
            t_time.text = tp['tst'].isoformat()[:19]+'Z'
            # t.append(Comment(u'#%s %s' % (dbid, topic)))
            trackpoints.append(t)

        root.append(gpxtrack)
        for trackpoint in trackpoints:
            segment.append(trackpoint)

        s.write(prettify(root))



    content_type = 'application/binary'
    if fmt in mimetype:
        content_type = mimetype[fmt]

    s.seek(0, os.SEEK_END)
    octets = s.tell()

    response.content_type = content_type
    response.headers['Content-Disposition'] = 'attachment; filename="%s.%s"' % (trackname, fmt)
    response.headers['Content-Length'] = str(octets)

    return s.getvalue()

@app.route('/api/getGeoJSON', method='POST')
def get_geoJSON():
    data = json.load(bottle.request.body)

    # needs LOTS of error handling

    usertid = data.get('usertid')
    from_date = data.get('fromdate')
    to_date = data.get('todate')
    spacing = int(data.get('spacing', POINT_KM))

    from_date = normalize_date(from_date)
    to_date   = normalize_date(to_date)

    track = getDBdata(usertid, from_date, to_date, spacing)

    last_point = [None, None]

    collection = {
            'type' : 'FeatureCollection',
            'features' : [],        # [ geo, <list of points> ]
    }


    geo = {
            'type' : 'Feature',
            'geometry' : {
                    'type' : 'LineString',
                    'coordinates' : []
                  },
            'properties' : {
                    'description' : "an OwnTracks track",  # updated below
                  },
    }

    pointlist = []
    track_coords = []
    kilometers = track_length(track)

    # bounding box
    lat_min = 180
    lat_max = -180
    lon_min = 90
    lon_max = -90

    for tp in track:

        lat = tp['lat']
        lon = tp['lon']
        tst = tp['tst']

        if lat > lat_max:
            lat_max = lat
        if lat < lat_min:
            lat_min = lat
        if lon > lon_max:
            lon_max = lon
        if lon < lon_min:
            lon_min = lon


        track_coords.append( [ lon, lat ] )


        distance = None
        if last_point[0] is not None:
            distance = haversine.haversine(lon, lat, last_point[0], last_point[1])

        if last_point[0] is None or distance > spacing:
            last_point = [lon, lat]
            point = {
                    'type'  : 'Feature',
                    'geometry' : {
                        'type'  : "Point",
                        'coordinates' : [lon, lat],
                    },
                    'properties' : {
                        'description' : "%s: %s" % (tst, tp.get('addr', 'Unknown location'))
                    }
            }
            pointlist.append(point)


    geo['geometry']['coordinates'] = track_coords
    geo['properties']['description'] = "Track length: %.2f km" % kilometers

    collection['features'] = [ geo ]
    for p in pointlist:
        collection['features'].append(p)

    # Experiment: geofences
    fences = []

    for f in getDBwaypoints(usertid, lat_min, lat_max, lon_min, lon_max):
        fence = {
                    'type'  : 'Feature',
                    'geometry' : {
                        'type'  : "Point",
                        'coordinates' : [f['lon'], f['lat']],
                    },
                    'properties' : {
                        'description' : f['name'],
                        'geofence': {
                            'radius' : f['rad'],
                        },
                    }
            }
        collection['features'].append(fence)


    return collection

@app.route('/api/onevehicle/<tid>', method='GET')
def onevehicle(tid):

    params = {
        'tid'       : tid,
        'tstamp'    : None,
        'version'   : None,
        'vbatt'     : None,
        'vext'      : None,
        'imei'      : None,
        'npubs'     : None,
        'addr'      : None,
        'cc'        : None,
        'lat'       : None,
        'lon'       : None,
        'modif'     : None,
        'compass'   : None,
    }

    key = "tid:%s" % tid
    tidkey = redis.get(key)

    data = redis.hgetall(tidkey)
    for k in params:
        if k in data:
            params[k] = data[k]


    response.content_type = 'text/plain; charset: UTF-8'
    return template('onevehicle', params)

@app.route("/api/flotbatt/<voltage>", method="GET")
def flotbatt(voltage):


    battlevels = []

    # Find all devices in Redis and add their vbatt into a list

    for device in redis.keys("t:*"):
        data = redis.hgetall(device)

        tid = data.get('tid')
        vbatt = data.get('vbatt')

        if tid is not None and vbatt is not None:
            vbatt = float(vbatt)

            battlevels.append( [tid, vbatt] )

    flot = {
        'label' : 'Batt',
        'data'  : sorted(battlevels),
    }

    return flot


@app.route('/<filename:re:.*\.js>')
def javascripts(filename):
    return static_file(filename, root='static')

#    return static_file(filename, root='files', mimetype='image/png')

# <link type='text/css' href='yyy.css' rel='stylesheet' >
@app.route('/<filename:re:.*\.css>', name='css')
def stylesheets(filename):
    return static_file(filename, root='static')

@app.get('/<filename:re:.*\.(jpg|gif|png|ico)>')
def images(filename):
    return static_file(filename, root='static')

# from: http://michael.lustfield.net/nginx/bottle-uwsgi-nginx-quickstart
class StripPathMiddleware(object):
    '''
    Get that slash out of the request
    '''
    def __init__(self, a):
        self.a = a
    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
        return self.a(e, h)

if __name__ == '__main__':
    pistaconf = cf.config('pista')
    bottle.debug(True)
    bottle.run(app=StripPathMiddleware(app),
        # server='python_server',
        host=pistaconf.get('listen_host', "127.0.0.1"),
        port=pistaconf.get('listen_port', 8080),
        reloader=True)
