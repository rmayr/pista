#!/usr/bin/env python

from data import *
from data import _dM, _dK, _dB, _dH, _dN, _dG
import paho.mqtt.client as paho
import time
import json
import os
import sys
from threading import Thread
import random

PAUSE = 15  # seconds. Fractions (e.g. 0.3) OK

TIDS = {
    'dK' : _dK(),
    'dB' : _dB(),
    'dH' : _dH(),
    'dM' : _dM(),
    'dN' : _dN(),
    'dG' : _dG(),
}

info = {
    'dK' : "your driver: Janine",
    'dB' : "su conductor: Jose-Maria",
    'dM' : "Ihr Fahrer: Hans Werner",
    'dH' : "votre conductrice: Anne Marie",
    'dN' : 'Germany-France',
    'dG' : 'ruta: norte',
    'M1' : "next tour: June",
}

clientid = 'demo-simulator-%s' % os.getpid()
mqttc = paho.Client(clientid, clean_session=True, userdata=None, protocol=3)
mqttc.username_pw_set(os.getenv('SIMUSERNAME', ''), os.getenv('SIMPASSWORD', ''))
mqttc.connect("localhost", 1883, 60)

mqttc.loop_start()

def coll2json(loc, alarm=None):

    data = {
        'tst' : int(time.time()),
        'tid' : loc.tid,
        'lat' : loc.lat,
        'lon' : loc.lon,
        '_type' : 'location',
        't'    : loc.t,
        'cog'  : loc.cog,
        'dist' : loc.dist,
        'trip' : loc.trip,
        'alt'  : loc.alt,
        'vel'  : loc.vel,
    }

    if alarm and loc.tid == 'dB':
        data['t'] = 'a'
        data['event'] = 'leave'
        data['desc'] = 'airport'

    status = 1
    if loc.t == 'f' or loc.t == 'L':
        status = -1
    mqttc.publish('owntracks/demo/%s/status' % loc.tid, status, qos=0, retain=True)

    return json.dumps(data)

def myfunc(tid, loclist, n=0):
    print "Here is ", tid, " with ", len(loclist)
    run = 1
    while run:
        alarm = 1
        try:
            # Periodically force M1 to be offline
            mqttc.publish('owntracks/demo/M1/status', '0', qos=0, retain=True)

            # Forwards ....
            for l in loclist:
                payload = coll2json(l, alarm)
                if alarm == 1:
                    alarm = 0
                mqttc.publish('owntracks/demo/%s' % tid, payload, qos=0, retain=True)
                time.sleep(PAUSE + n)

            # ... and Reverse!
            for l in reversed(loclist):
                payload = coll2json(l, alarm=0)
                mqttc.publish('owntracks/demo/%s' % tid, payload, qos=0, retain=True)
                time.sleep(PAUSE + n)

        except KeyboardInterrupt:
            sys.exit(0)
        run = 1
    
def startup(tid, status, n=0):
    imei = '1234567890123%d' % n
    gpio = 1
    if status != 1:
        gpio = 0

    objs = {
        'status'        : status,
        'start'         : '%s 0.10.97 20141202T084939Z' % (imei),
        'gpio/7'        : gpio,
        'voltage/batt'  : '4.%s' % random.randint(2, 6),
        'voltage/ext'   : '13.%s' % random.randint(2, 6),
        'operators'     : '26202 +26201 +26203 +26207',
        'info'          : info[tid],
    }

    for o in objs:
        topic = 'owntracks/demo/%s/%s' % (tid, o)
        payload = objs[o]

        mqttc.publish(topic, payload, qos=0, retain=True)

# Create an inactive vehicle

startup('M1', -1)
payload = coll2json(
        Loc('M1', 45.605092, 14.184552, 285, 19, 57, 'l', 886, 26850)
        )
mqttc.publish('owntracks/demo/M1', payload, qos=0, retain=True)


n = 0
for tid in TIDS:
    startup(tid, 1, n)
    try:
        t = Thread(target=myfunc, args=(tid, TIDS[tid], n, ))
        t.start()
    except KeyboardInterrupt:
        sys.exit(0)
    n = n + 2

