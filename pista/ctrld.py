#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'

import sys
sys.path.insert(0, './lib')
sys.path.insert(0, './../o2s/lib')
import os
import logging
import bottle
from bottle import response, template, static_file, request
import json
import time
from cf import conf
from authschema import User, Acl, fn, sql_db
from dbschema import Location
import hashing_passwords as hp
import paho.mqtt.client as paho


SCRIPTNAME = os.path.splitext(os.path.basename(__file__))[0]
LOGFILE    = os.getenv(SCRIPTNAME.upper() + 'LOG', SCRIPTNAME + '.log')
LOGLEVEL   = logging.INFO
#LOGLEVEL   = logging.DEBUG
LOGFORMAT  = '%(asctime)-15s %(levelname)-5s [%(module)s] %(message)s'

logging.basicConfig(filename=LOGFILE, level=LOGLEVEL, format=LOGFORMAT)
logging.info("Starting %s" % SCRIPTNAME)
logging.info("INFO MODE")
logging.debug("DEBUG MODE")

app = application = bottle.Bottle()

def notauth(reason):
    return bottle.HTTPResponse(status=403, body=json.dumps({"message": reason}))

def auth(username, password, apns_token=None):

    if username is None or password is None:
        return False

    try:
        sql_db.connect()
    except Exception, e:
        logging.error("%s" % str(e))
        return False

    pwhash = None
    try:
        u = User.get(User.username == username)
        pwhash = u.pwhash
    except User.DoesNotExist:
        logging.debug("User ", username, " does not exist")
        return False
    except Exception, e:
        raise



    match = hp.check_hash(password, pwhash)
    logging.debug('Hash match for %s (%s): %s' % (username, pwhash, match))

    if match == True and apns_token is not None:
        tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        q = User.update(token = apns_token, tstamp = tstamp).where(User.username == username)
        q.execute()

    return match

@app.route('/ext/')
def show_index():
    return "Hola!"

@app.route('/ext/conf', method='POST')
def conf():
    resp = {}
    data = bottle.request.body.read()

    username = request.forms.get('username')
    password = request.forms.get('password')
    apns_token = request.forms.get('token')

    authorized = auth(username, password, apns_token)

    logging.info("CONF: (username=%s, token=%s) authorized=%s" % (username, apns_token, authorized))

    if authorized == False:
        return notauth("Not authenticated")

    topic_list = []

    # Select list of topics for this user. Attempt to expand %u which the client
    # won't understand. %c loses out -- that won't work, so no point returning
    # those.
    try:
        for sub in Acl.select().where(Acl.username == username):
            new_sub = sub.topic.replace('%u', username)
            if '%c' not in new_sub:
                topic_list.append(new_sub)
    except Exception, e:
        logging.error("Can't query ACL for topic list: %s" % (str(e)))

    resp = {
            '_type'         : 'configuration',
            'topicList'     : topic_list,
            'host'          : 'demo.owntracks.de',
            'port'          : 8883,
            'tls'           : 1,
            'auth'          : 1,
            'clientid'      : 'iosCTRL-' + username,
            'trackurl'      : 'https://demo.owntracks.de/ext/ctrl/tracks/%s' % username,
            'username'      : username,  # Return to client for MQTT connection
            'password'      : password,  # Return to client for MQTT connection
            'certurl'       : "https://demo.owntracks.de/ext/ctrl/cacert.pem",
        }

    if username == 'jp2':
        resp['trackurl'] = None

    response.content_type = 'application/json'
    response.status = 200
    # return json.dumps(resp, sort_keys=True, separators=(',',':'))
    return json.dumps(resp, sort_keys=True, indent=2)


@app.route('/ext/ctrl/cacert.pem', method='GET')
def cacert():
    ''' Return the PEM-encoded CA certificate for the connection
        to the MQTT broker. '''

    # FIXME
    f = open('demo-8883.crt')
    pem = f.read()
    f.close()


    response.content_type = 'application/x-pem-file'
    return pem


# TRACKS ---------------------------------------------------------------
@app.route('/ext/ctrl/tracks/<user>', method='POST')
def ctrl_trackdump(user):
    data = bottle.request.body.read()

    track = []
    status = 200

    username = request.forms.get('username')
    password = request.forms.get('password')
    tid = request.forms.get('tid')
    try:
        nrecs = int(request.forms.get('nrecs'))
    except:
        nrecs = 10
    topic = request.forms.get('topic')

    authorized = auth(username, password)

    logging.info("TRACK: (username=%s) authorized=%s" % (username, authorized))

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
            logging.debug("sub %s (%s) => %s" % (sub, new_sub, matches))
            if matches:
                track_authorized = True
                status = 200
                break
    except Exception, e:
        logging.error("Can't query ACL: %s" % (str(e)))



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

    logging.info("TRACK: (username=%s, tid=%s, topic=%s) RETURN %s recs" % (username, tid, topic, len(track)))

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
    bottle.run(app,
        host='127.0.0.1',
        port=8809)
