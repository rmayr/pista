#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import os
import sys
import owntracks
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
import paho.mqtt.client as paho
from owntracks.dbschema import db, Geo, Location, Waypoint, User, Acl, Inventory, JOIN_LEFT_OUTER, fn, createalltables, dbconn, RAWdata
from owntracks.auth import PistaAuth
from owntracks import haversine
import pytz
import httpagentparser
HAVE_XLS=True
try:
    import xlwt
except ImportError:
    HAVE_XLS=False

log = logging.getLogger(__name__)

createalltables()

auth = PistaAuth()

POINT_KM = 20

app = application = bottle.Bottle()
bottle.SimpleTemplate.defaults['get_url'] = app.get_url

def notauth(reason):
    return bottle.HTTPResponse(status=403, body=reason)

def check_auth(username, password):

    return auth.check(username, password, apns_token=None)

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

def utc_time(s, tzname='UTC'):
    ''' Convert time string 's' which is in "local time" to UTC
        and return that as a string.
        '''

    utc = pytz.utc
    local_zone = pytz.timezone(tzname)

    dt1 = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    local_time = local_zone.localize(dt1)
    utc_time = local_time.astimezone(utc)

    new_s = utc_time.strftime("%Y-%m-%d %H:%M:%S")
    log.debug("utc_time: TZ={0}: {1} => {2}".format(tzname, s, new_s))
    return new_s

def utc_to_localtime(dt, tzname='UTC'):
    ''' Convert datetime 'dt' which is in UTC to the timezone specified as 'tzname' '''

    utc = pytz.utc
    local_zone = pytz.timezone(tzname)

    utc_time = utc.localize(dt)
    local_time = utc_time.astimezone(local_zone)

    new_s = local_time.strftime("%Y-%m-%d %H:%M:%S")
    # log.debug("utc_time: TZ={0}: {1} => {2}".format(tzname, dt, new_s))
    return new_s


def getDBdata(usertid, from_date, to_date, spacing, tzname='UTC'):

    track = []

    from_date = normalize_date(from_date)
    to_date   = normalize_date(to_date)

    from_date = "%s 00:00:00" % from_date
    to_date = "%s 23:59:59" % to_date

    from_date = utc_time(from_date, tzname)
    to_date = utc_time(to_date, tzname)

    log.debug("getDBdata: FROM={0}, TO={1}".format(from_date, to_date))

    dbconn()

# select tst, lat, lon, l.ghash, addr from location l left join geo g on l.ghash = g.ghash where tid = 'B2';

    query = (Location
                .select(Location, Geo.addr.alias('addr'))
                .join(Geo, JOIN_LEFT_OUTER, on=(Location.ghash == Geo.ghash)).
                where(
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
                'dist' : l.dist,
                'trip' : l.trip,
            }

            track.append(tp)
        except:
            pass

    log.info("getDBdata: FROM={0}, TO={1} returns {2} points for {3}".format(from_date, to_date, len(track), usertid))
    return track

def getDBwaypoints(usertid, lat_min, lat_max, lon_min, lon_max):

    waypoints = []

    lat_min = float(lat_min)
    lat_max = float(lat_max)
    lon_min = float(lon_min)
    lon_max = float(lon_max)

    dbconn()
    query = Waypoint.select().where(
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
        log.debug("User {0} does not exist".format(username))
        return []
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

    log.debug("User {0} gets tidlist={1}".format(username, ",".join(tidlist)))

    return sorted(set(tidlist))

def getinventorytopics(username):
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
        log.debug("User {0} does not exist".format(username))
        return []
    except Exception, e:
        raise

    if not superuser:
        query = (Acl.select(Acl). where(
                    (Acl.username == username)
                ))
        sublist = [ q.topic for q in query.naive() ]
    else:
        sublist.append('#')

    # Find distinct topic, tid combinations in Inventory table and
    # let Paho check if subscription matches

    topiclist = []

    query = (Inventory.select(Inventory.tid, Inventory.topic)
                    .distinct()
                    .order_by(Inventory.tid)
                    )
    for q in query:
        for sub in sublist:
            if paho.topic_matches_sub(sub, q.topic):
                topiclist.append( dict(tid=q.tid, topic=q.topic) )

    return topiclist


#-----------------

@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'

@app.route('/')
def root_page():
    return template('index', pistapages=cf.g('pista', 'pages'), isdemo=cf.g('pista', 'is_demo'))

@app.route('/index')
@auth_basic(check_auth)
def index():
    return template('index', pistapages=cf.g('pista', 'pages'), isdemo=cf.g('pista', 'is_demo'))

@app.route('/about')
def page_about():
    return template('about', pistapages=cf.g('pista', 'pages'))

@app.route('/jobedit')
def page_jobedit():
    return template('jobedit', pistapages=cf.g('pista', 'pages'))

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

    current_user = request.auth[0]
    usertids = getusertids(current_user)

    device_list = []

    # Find all devices in Inventory and extract their info into a list
    # of objects. Ensure values of hash keys are None if unset or
    # the template will bail out.

    try:
        query = (Inventory
                .select(Inventory)
                .where(
                    (Inventory.tid << usertids)
                )
            )
        query = query.order_by(Inventory.tid.asc())
        for q in query.naive():
            try:
                device_list.append({
                    'tid'       : q.tid,
                    'imei'      : q.imei,
                    'version'   : q.version,
                    'tstamp'    : q.startup,
                    'topic'     : q.topic,
                    })
            except:
                pass
    except:
        pass        # device_list will be empty => no data, which is OK here


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
    activo = cf.g('features', 'activo', False)
    return template('table', pistapages=cf.g('pista', 'pages'), activo=activo)

@app.route('/jobs')
@auth_basic(check_auth)
def page_job():
    return template('jobs', pistapages=cf.g('pista', 'pages'), have_xls=HAVE_XLS, isdemo=0)

@app.route('/tracks')
@auth_basic(check_auth)
def page_tracks():

    isdemo = isdemo=cf.g('pista', 'is_demo')
    if isdemo == True:
        isdemo = 1
    else:
        isdemo = 0

    return template('tracks', pistapages=cf.g('pista', 'pages'), have_xls=HAVE_XLS, isdemo=isdemo)

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

    newconf['activo'] = cf.g('features', 'activo', False)
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

    dbconn()

    usertids = getusertids(current_user)

    allowed_tids = []
    for t in usertids:
        allowed_tids.append({
            'id' : t,
            'name' : t,
        })

    log.debug("/api/userlist returns: {0}".format(json.dumps(allowed_tids)))
    return dict(userlist=allowed_tids)

@app.route('/api/inventorytopics')
@auth_basic(check_auth)
def inventorytopics():
    ''' Get list of username - topic pairs to populate a select box
        the id in that select will be set to tid|topic.
        This is pulled in from the Inventory table. What we're trying
        to accomplish is to find a TID -> topic association. '''

    current_user = request.auth[0]

    dbconn()

    usertids = getinventorytopics(current_user)

    allowed_tids = []
    for t in usertids:
        allowed_tids.append({
            'name' : t['tid'],
            'id' : t['topic'],
        })

    log.debug("/api/inventorytopics returns: {0}".format(json.dumps(allowed_tids)))
    return dict(userlist=allowed_tids)


# ?usertid=XX&fromdate=2014-08-19&todate=2014-08-20&format=txt
@app.route('/api/download', method='GET')
@auth_basic(check_auth)
def get_download():
    mimetype = {
        'csv':  'text/csv',
        'txt':  'text/plain',
        'gpx':  'application/gpx+xml',
        'xls':  'application/vnd.ms-excel',
    }

    EOL = "\n"
    os = 'unknown'
    user_agent = request.environ.get('HTTP_USER_AGENT')

    try:
        os = httpagentparser.detect(user_agent)['os']['name'].upper()
    except:
        pass

    if os == 'WINDOWS':
        EOL = "\r\n"

    log.debug("client OS = {0} ({1})".format(os, user_agent))

    current_user = request.auth[0]

    usertid = request.params.get('usertid')
    from_date = request.params.get('fromdate')
    to_date = request.params.get('todate')
    fmt = request.params.get('format')
    tzname = request.params.get('tzname', 'UTC')

    from_date = normalize_date(from_date)
    to_date   = normalize_date(to_date)

    # before allowing download check for usertid auth
    usertids = getusertids(current_user)
    if usertid not in usertids:
        log.warn("User {0} is not authorized to download data for tid={1}".format(current_user, usertid))
        return notauth(reason="Not authorized for this TID")

    if fmt not in mimetype:
        return { 'error' : "Unsupported download-type requested" }

    trackname = 'owntracks-%s-%s-%s' % (usertid, from_date, to_date)

    track = getDBdata(usertid, from_date, to_date, None, tzname)

    kilometers = track_length(track)

    sio = StringIO()
    s = codecs.getwriter('utf8')(sio)

    if fmt == 'txt':

        info = "Timestamp({0})".format(tzname)
        s.write("%-10s %-10s %s %s %s%s" % ("Latitude", "Longitude", info, "Speed", "Location", EOL))

        for tp in track:

            revgeo = tp.get('revgeo', "")
            vel = "%9d" % tp.get('vel', 0)

            s.write(u'%-10s %-10s %s %-14s %6s %s%s' % \
                (tp.get('lat'),
                tp.get('lon'),
                utc_to_localtime(tp.get('tst'), tzname),
                vel,
                tp.get('addr', ""),
                revgeo,
                EOL))
        s.write("%sTrip: %.2f kilometers%s" % (EOL, kilometers, EOL))

    if fmt == 'csv':

        tp = track[0]
        title = ""
        for key in tp.keys():
            title = title + u'"%s",' % key

        s.write("%s%s" % (title[0:-1], EOL))  # chomp last separator

        for tp in track:
            line = ""
            for key in tp:
                if key == 'tst':
                    tp['tst'] = utc_to_localtime(tp.get('tst'), tzname)
                line = line + u'"%s",' % tp[key]

            line = line[0:-1]   # chop last separator
            s.write(u'%s%s' % (line, EOL))

    if fmt == 'xls':
        if not HAVE_XLS:
            return  # FIXME

        cols = [ 'tst', 'lat', 'lon', 'alt', 'vel', 't', 'cog', 'dist', 'trip', 'cc', 'addr' ]

        font0 = xlwt.Font()
        font0.name = 'Arial'
        font0.colour_index = 2
        font0.bold = True

        style0 = xlwt.XFStyle()
        style0.font = font0

        courier = xlwt.Font()
        courier.name = 'Courier New'
        courier.bold = False

        fixed_style = xlwt.XFStyle()
        fixed_style.font = courier


        date_style = xlwt.XFStyle()
        date_style.num_format_str = 'D-MMM-YY HH:MM:SS'

        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('OwnTracks')

        coldesc = {
                      # Width, Heading,
            'tst'   : [ 25,     "Timestamp" ],
            'lat'   : [ 12,   "Latitude" ],
            'lon'   : [ 12,   "Longitude" ],
            'alt'   : [ None,   "Altitude (m)" ],
            'vel'   : [ None,   "Velocity (km)" ],
            't'     : [ 3,      "Trigger" ],
            'cog'   : [ 7,   "Course" ],
            'dist'  : [ None,   "Distance (m)" ],
            'trip'  : [ None,   "Trip (km)" ],
            'cc'    : [ 5,      "Country" ],
            'addr'  : [ 60,     "Location" ],
        }
        for c, txt in enumerate(cols):      # Heading
            if txt in coldesc:
                width, heading = coldesc[txt]
                if width is None:
                    width = len(heading)
                if width < len(heading):
                    width = len(heading)

                ws.col(c).width = 256 * width
                if heading is not None:
                    ws.write(0, c, heading, style0)
                else:
                    ws.write(0, c, txt, style0)
            else:
                ws.write(0, c, txt, style0)

        trip_start = trip_end = 0
        try:
            trip_start = int(track[0]['trip'] / 1000)
        except:
            pass
        r = 1
        for tp in track:
            ws.write(r, 0, tp.get('tst'), date_style)
            ws.write(r, 1, str(tp.get('lat')))
            ws.write(r, 2, str(tp.get('lon')))
            ws.write(r, 3, tp.get('alt'))
            ws.write(r, 4, tp.get('vel'))
            ws.write(r, 5, tp.get('t'), fixed_style)
            ws.write(r, 6, tp.get('cog'))
            ws.write(r, 7, tp.get('dist'))
            ws.write(r, 8, int(tp.get('trip') / 1000))
            ws.write(r, 9, tp.get('cc'), fixed_style)
            ws.write(r, 10, tp.get('addr'))

            trip_end = int(tp.get('trip', 0) / 1000)

            r = r + 1

        r = r + 1
        ws.write(r, 0, "Haversine dist (km)")
        ws.write(r, 1, round(kilometers, 2))

        r = r + 1
        ws.write(r, 0, "Total trip (km)")
        ws.write(r, 1, trip_end - trip_start)

        r = r + 2
        ws.write(r, 0, xlwt.Formula('HYPERLINK("http://owntracks.de";"OwnTracks.de")'),
                xlwt.easyxf(
                    'font: name Arial;'
                    'font: color red;'
                    'font: underline single;'
                ))

        wb.save(sio)


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

        root_string = prettify(root)
        root_string = root_string.replace('\n', EOL)
        s.write(root_string)



    content_type = 'application/binary'
    if fmt in mimetype:
        content_type = mimetype[fmt]

    octets = len(s.getvalue())

    response.content_type = content_type
    response.headers['Content-Disposition'] = 'attachment; filename="%s.%s"' % (trackname, fmt)
    response.headers['Content-Length'] = str(octets)

    return s.getvalue()

@app.route('/api/getGeoJSON', method='POST')
@auth_basic(check_auth)
def get_geoJSON():
    data = json.load(bottle.request.body)

    # needs LOTS of error handling

    usertid = data.get('usertid')
    from_date = data.get('fromdate')
    to_date = data.get('todate')
    spacing = int(data.get('spacing', POINT_KM))
    tzname = data.get('tzname', 'UTC')

    track = getDBdata(usertid, from_date, to_date, spacing, tzname)

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
        'jobname'   : None,
    }

    key = "tid:%s" % tid

    try:
        tidkey = redis.get(key)
        data = redis.hgetall(tidkey)
        for k in params:
            if k in data:
                params[k] = data[k]
    except:
        pass


    response.content_type = 'text/plain; charset: UTF-8'
    return template('onevehicle', params)

@app.route("/api/flotbatt/<voltage>", method="GET")
@auth_basic(check_auth)
def flotbatt(voltage):

    ''' Find all user's devices and add vbatt levels into list
        for HW page '''

    current_user = request.auth[0]
    usertids = getusertids(current_user)

    battlevels = []

    try:
        query = (Inventory
                .select(Inventory)
                .where(
                    (Inventory.tid << usertids)
                )
            )
        for q in query.naive():
            try:
                battlevels.append( [q.tid, float(q.vbatt)] )
            except:
                pass
    except Exception, e:
        log.warn("User {0} failed Inventory query on flotbatt: {1}".format(current_user, str(e)))
        pass

    flot = {
        'label' : 'Batt',
        'data'  : sorted(battlevels),
    }

    return flot

@app.route("/utility/battery.json", method="GET")
def json_batt():

    result = []
    dbconn()
    query = (RAWdata.select(RAWdata.tst, RAWdata.payload)
            .where(
                RAWdata.topic == 'owntracks/gw/356612028111492/voltage/batt'
            )
            )

    query = query.order_by(RAWdata.tst.desc()).limit(190)

    time_format = "%Y-%m-%d %H:%M:%S"
    for q in query.naive():
        tstamp = q.tst.strftime(time_format)
        print tstamp, q.payload
        result.append( { 'tst' : tstamp, 'batt' : float(q.payload) } )

    j = json.dumps(result)
    print j
    return j


@app.route('/<filename:re:.*\.js>')
def javascripts(filename):
    return static_file(filename, root='static')

#    return static_file(filename, root='files', mimetype='image/png')

# <link type='text/css' href='yyy.css' rel='stylesheet' >
@app.route('/<filename:re:.*\.css>', name='css')
def stylesheets(filename):
    return static_file(filename, root='static')

#@app.get('/<filename:re:/img/clear.png>')
#def images(filename):
#    return static_file(filename, root='static')

@app.get('/<filename:re:.*\.(jpg|gif|png|ico)>')
def images(filename):
    return static_file(filename, root='static')

@app.get('/<filename:re:.*\.(eot|ttf|woff|svg|woff2)>')
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
    log.info("Bottle returns")
