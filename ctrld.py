#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import sys
import os
import owntracks
import logging
import bottle
from bottle import response, template, static_file, request
import json
import time
from owntracks import cf
from owntracks.dbschema import db, User, Acl, Params, fn, Location, createalltables
import paho.mqtt.client as paho
from owntracks.auth import PistaAuth

log = logging.getLogger(__name__)

cacert_file = cf.g('ctrld', 'cacert_file')
if not os.path.isfile(cacert_file) or not os.access(cacert_file, os.R_OK):
    log.error("Cannot open cacert_file ({0})".format(cacert_file))
    sys.exit(2)

createalltables()

auth = PistaAuth()

app = application = bottle.Bottle()

def notauth(reason):
    return bottle.HTTPResponse(status=403, body=json.dumps({"message": reason}))

@app.route('/')
def show_index():
    return "Hola!"

@app.route('/conf', method='POST')
def conf():
    resp = {}
    data = bottle.request.body.read()

    username = request.forms.get('username').strip()
    password = request.forms.get('password').strip()
    clientid = request.forms.get('clientid').strip()
    apns_token = request.forms.get('token')

    authorized = auth.check(username, password, apns_token)

    if clientid is None or len(clientid) < 1:
        clientid = ''

    log.info("CONF: (username=%s, token=%s) authorized=%s" % (username, apns_token, authorized))

    if authorized == False:
        return notauth("Not authenticated")

    mqtthost    = 'demo.owntracks.de'
    mqttport    = 8883
    mqtt_tls    = 1
    mqtt_auth   = 1
    mqtt_username = username
    mqtt_password = password
    certurl     = "https://demo.owntracks.de/ctrld/cacert.pem"
    trackurl    = 'https://demo.owntracks.de/ctrld/tracks/%s' % username

    try:
        params = (Params
                    .select()
                    .join(User)
                    .where(
                        (User.username == username)
                    )
                    .get())
        if params.host is not None:
            mqtthost = params.host
        if params.port is not None:
            mqttport = params.port
        if params.tls is not None:
            mqtt_tls = params.tls
        if params.auth is not None:
            mqtt_auth = params.auth
        if params.mqttuser is not None:
            mqtt_username = params.mqttuser
        if params.mqttpass is not None:
            mqtt_password = params.mqttpass
        if params.certurl is not None:
            certurl = params.certurl
        if params.trackurl is not None:
            trackurl = params.trackurl

    except Exception, e:
        log.info("There are no params for %s: %s" % (username, str(e)))
        pass

    topic_list = []

    # Select list of topics for this user. Attempt to expand %u which the client
    # won't understand. %c loses out -- that won't work, so no point returning
    # those.
    try:
        for sub in Acl.select().where(Acl.username == username):
            if sub.topic.startswith('_'):    # FIXME this is temporary
                continue
            new_sub = sub.topic.replace('%u', username)
            if '%c' not in new_sub:
                # Ensure that CTRL get's correct topics. In particular, not more
                # than 3 'parts' ending in '#'

                parts = new_sub.split('/')
                nparts = len(parts)
                if new_sub.startswith('/'):
                    nparts = nparts - 1
                new_topic = new_sub
                if nparts > 3 and new_sub.endswith('/#'):
                    new_topic = new_sub[0:-2]
                topic_list.append(new_topic)
    except Exception, e:
        log.error("Can't query ACL for topic list: %s" % (str(e)))

    mqtt_id = 'iosCTRL.' + username + '.' + clientid
    mqtt_id = mqtt_id[0:22]

    resp = {
            '_type'         : 'configuration',
            'topicList'     : topic_list,
            'host'          : mqtthost,
            'port'          : mqttport,
            'tls'           : mqtt_tls,
            'auth'          : mqtt_auth,
            'clientid'      : mqtt_id,
            'trackurl'      : trackurl,
            'username'      : mqtt_username,  # Return to client for MQTT connection
            'password'      : mqtt_password,  # Return to client for MQTT connection
            'certurl'       : certurl,
        }

    if username == 'jp2':
        resp['trackurl'] = None

    response.content_type = 'application/json'
    response.status = 200
    # return json.dumps(resp, sort_keys=True, separators=(',',':'))
    return json.dumps(resp, sort_keys=True, indent=2)


@app.route('/cacert.pem', method='GET')
def cacert():
    ''' Return the MQTT broker's PEM-encoded CA certificate '''

    pem = None
    try:
        f = open(cacert_file)
        pem = f.read()
        f.close()
    except Exception, e:
        log.error("Cannot read PEM from {0}: {1}".format(cacert_file, str(e)))
        response.status = 404
        response.content_type = 'text/plain'
        return "404 Cacert Not found"


    response.content_type = 'application/x-pem-file'
    return pem


# TRACKS ---------------------------------------------------------------
@app.route('/tracks/<user>', method='POST')
def ctrl_trackdump(user):
    data = bottle.request.body.read()

    track = []
    status = 200

    try:
        db.connect()
    except Exception, e:
        log.error("%s" % str(e))
        return False

    username = request.forms.get('username').strip()
    password = request.forms.get('password').strip()
    tid = request.forms.get('tid').strip()
    try:
        nrecs = int(request.forms.get('nrecs'))
    except:
        nrecs = 10
    topic = request.forms.get('topic').strip()

    authorized = auth.check(username, password)

    log.info("TRACK: (username=%s) authorized=%s" % (username, authorized))

    if authorized == False:
        return notauth("Not authenticated")

    if topic is None:
        return notauth("topic is empty")


    # Check whether this user is authorized to download track for this topic.
    # Get list of topics from ACL table and compare. Caveat: %c escapes are
    # not supported here and will thus not match.

    track_authorized = False
    message = "Not authorized"
    status = 403

    try:
        query = (Acl.select(Acl). where(
                    (Acl.username == username)
                    ))
        for s in query.naive():
            sub    = s.topic

            new_sub = sub.replace('%u', username)
            matches = paho.topic_matches_sub(sub, topic)
            log.debug("sub %s (%s) => %s" % (sub, new_sub, matches))
            if matches:
                track_authorized = True
                status = 200
                break
    except Exception, e:
        log.error("Can't query ACL: %s" % (str(e)))



    if nrecs is None or int(nrecs) < 1:
        nrecs = 50
    if nrecs > 600:
        nrecs = 600

    track = []

    if track_authorized == True:
        message = "OK"
        status = 200
        query = (Location
                    .select(Location).
                    where(
                        (Location.topic == topic)
                        )
                    ).order_by(Location.tst.desc()).limit(nrecs)
        for l in query.naive():

            dbid    = l.id
            lat     = float(l.lat)
            lon     = float(l.lon)
            dt      = l.tst

            try:
                tp = {
                    'lat' : float(l.lat),
                    'lon' : float(l.lon),
                    'tst' : int(dt.strftime('%s')),
                }

                track.append(tp)
            except:
                pass

    log.info("TRACK: (username=%s, tid=%s, topic=%s) RETURN %s recs" % (username, tid, topic, len(track)))

    data = {
        'topic'    : topic,
        'message'  : message,
        'tstamp'   : time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(time.time()))),
        'track'    : track,
    }


    response.content_type = 'application/json'
    response.status = status
    return json.dumps(data, sort_keys=True, indent=2)
    return json.dumps(data, sort_keys=True, separators=(',',':'))

#  ---------------------------------------------------------------

if __name__ == '__main__':

    ctrldconf = cf.config('ctrld')
    bottle.debug(True)
    bottle.run(app,
        # server='python_server',
        host=ctrldconf.get('listen_host', "127.0.0.1"),
        port=ctrldconf.get('listen_port', 8809),
        )
