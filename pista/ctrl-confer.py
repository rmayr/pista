#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'

import sys
sys.path.insert(0, './lib')
sys.path.insert(0, './../o2s/lib')
import bottle
from bottle import response, template, static_file, request
import json
import time
from cf import conf
from authschema import User, fn, sql_db
import hashing_passwords as hp

app = application = bottle.Bottle()

def notauth(reason):
    return bottle.HTTPResponse(status=403, body=json.dumps({"message": reason}))

def auth(username, password, apns_token):
    print "***DEBUG AUTH CONF: username=%s, pw=[%s], TOK=%s" % ( username, password, apns_token)

    if username is None or password is None:
        return False

    try:
        sql_db.connect()
    except Exception, e:
        print str(e)
        return False

    pwhash = None
    try:
        u = User.get(User.username == username)
        pwhash = u.pwhash
    except User.DoesNotExist:
        print "User ", username, " does not exist"
        return False
    except Exception, e:
        raise

    print "GOT hash == [%s]" % pwhash


    match = hp.check_hash(password, pwhash)
    print "Hash match for [%s]: %s" % (username, match)

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
    status = 200
    resp = {}
    data = bottle.request.body.read()

    username = request.forms.get('username')
    password = request.forms.get('password')
    apns_token = request.forms.get('token')

    authorized = auth(username, password, apns_token)
    if authorized == False:
        return notauth("Not authenticated")

    if not authorized:
        status = 403
    else:
        topics = [ 'owntracks/+/MV', 'owntracks/+/+' ]  # FIXME: from DB
        resp = {
            '_type'         : 'configuration',
            'topicList'     : topics,
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
    response.status = status
    # return json.dumps(resp, sort_keys=True, separators=(',',':'))
    return json.dumps(resp, sort_keys=True, indent=2)


@app.route('/ext/ctrl/cacert.pem', method='GET')
def cacert():
    f = open('demo-8883.crt')
    pem = f.read()
    f.close()


    response.content_type = 'application/x-pem-file'
    return pem

if __name__ == '__main__':
    bottle.run(app,
        host='127.0.0.1',
        port=8809)
