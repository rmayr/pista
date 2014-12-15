#!/usr/bin/env python

from data import *
from data import _dM
import paho.mqtt.client as paho
import time
import json
import os
import sys
from threading import Thread
import random

TIDS = {
#    'dK' : _dK(),
#    'dB' : _dB(),
#    'dH' : _dH(),
    'dM' : _dM(),
}

clientid = 'demo-simulator-%s' % os.getpid()
mqttc = paho.Client(clientid, clean_session=True, userdata=None, protocol=3)
mqttc.username_pw_set('o2sagent', 'f000')
mqttc.connect("localhost", 1883, 60)

mqttc.loop_start()

def coll2json(loc):
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

    return json.dumps(data)

def myfunc(tid, loclist):
    print "Here is ", tid, " with ", len(loclist)
    pause = 0.3
    run = 1
    while run:
        try:
            # Forwards ....
            for l in loclist:
                payload = coll2json(l)
                mqttc.publish('owntracks/demo/%s' % tid, payload, qos=0, retain=True)
                time.sleep(pause)

            # ... and Reverse!
            for l in reversed(loclist):
                payload = coll2json(l)
                mqttc.publish('owntracks/demo/%s' % tid, payload, qos=0, retain=True)
                time.sleep(pause)

        except KeyboardInterrupt:
            sys.exit(0)
        run = 1
    
def startup(tid):
    imei = '1234567890123%s' % random.randint(11, 20)
    objs = {
        'status'        : '1',
        'start'         : '%s 0.10.97 20141202T084939Z' % (imei),
        'gpio/7'        : '1',
        'voltage/batt'  : '4.%s' % random.randint(2, 6),
        'voltage/ext'   : '13.%s' % random.randint(2, 6),
        'operators'     : '26202 +26201 +26203 +26207',
    }

    for o in objs:
        topic = 'owntracks/demo/%s/%s' % (tid, o)
        payload = objs[o]

        mqttc.publish(topic, payload, qos=0, retain=True)

for tid in TIDS:
    startup(tid)
    try:
        t = Thread(target=myfunc, args=(tid, TIDS[tid],))
        t.start()
    except KeyboardInterrupt:
        sys.exit(0)

