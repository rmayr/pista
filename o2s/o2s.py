#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, './lib')
from wredis import Wredis
import time
import datetime
from revgeo import RevGeo
import paho.mqtt.client as paho
import ssl
import json
import os
from cf import conf
import socket
import mobile_codes
from dbschema import Location, Waypoint, RAWdata, Operators, sql_db
import io
import csv
import imp

cf = conf(os.getenv('WAPPCONFIG', 'o2s.conf'))

SEEN_DRIVING = 1200
MAX_VOLTAGES = 10
LASTLOC_EXPIRY = 3600

geo = RevGeo(cf.config('revgeo'))
redis = None
if cf.g('features', 'redis', False) == True:
    redis = Wredis(cf.config('redis'))

base_topics = []

alarm_plugin = None
if cf.g('features', 'alarm') is not None:
    try:
        alarm_plugin = imp.load_source('alarmplugin', cf.g('features', 'alarm'))
    except Exception, e:
        # logging.info("Can't import storage_plugin %s: %s" % (storage_plugin, e))
        print e
        sys.exit(2)

if sys.version < '3':
    import codecs
    def u(x):
        return codecs.unicode_escape_decode(x)[0]
else:
    def u(x):
        return x

def save_rawdata(topic, payload):
    if cf.g('features', 'rawdata', False) == False:
        return

    rawdata = {
        'topic'  : topic,
        'tst'    : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(time.time()))),
        'payload' : payload,
    }
    rd = RAWdata(**rawdata)
    rd.save()

def on_connect(mosq, userdata, rc):
    if rc != 0:
        print "MQTT connect: %s" % rc
        sys.exit(1)

    for t in base_topics:
        mqttc.subscribe("%s/+" % t, 0)
        mqttc.subscribe("%s/+/waypoints" % t, 0)
        if cf.g('features', 'plmn', False) == True:
            mqttc.subscribe("%s/+/operators" % t, 0)
            mqttc.subscribe("%s/+/operators/+" % t, 0)
        mqttc.subscribe("%s/+/cmd/#" % t, 0)
        mqttc.subscribe("%s/+/alarm" % t, 0)
        mqttc.subscribe("%s/+/start" % t, 0)
        mqttc.subscribe("%s/+/status" % t, 0)
        mqttc.subscribe("%s/+/voltage/+" % t, 0)
        mqttc.subscribe("%s/+/gpio/+" % t, 0)

def on_disconnect(mosq, userdata, rc):
    reasons = {
       '0' : 'Connection Accepted',
       '1' : 'Connection Refused: unacceptable protocol version',
       '2' : 'Connection Refused: identifier rejected',
       '3' : 'Connection Refused: server unavailable',
       '4' : 'Connection Refused: bad user name or password',
       '5' : 'Connection Refused: not authorized',
    }
    print "Disconnected: code=%s (%s)" % (rc, reasons.get(rc, 'unknown'))

def on_cmd(mosq, userdata, msg):
    if msg.retain == 1 or len(msg.payload) < 0:
        return

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

def device_name(topic, subtopic=None):
    ''' find base topic name from topic and subtopic. E.g. if
        topic == 'owntracks/gw/JP/start' and subtopic == '/start'
        return 'owntracks/gw/JP'
        '''

    device = topic
    if subtopic is not None:
        if device.endswith(subtopic):
            device = device[:-len(subtopic)]
    return device

def rkey(prefix, topic, subtopic=None):
    ''' construct a Redis key '''

    return "%s:%s" % (prefix, device_name(topic, subtopic))

def on_status(mosq, userdata, msg):
    if msg.retain == 1 or len(msg.payload) < 0:
        return

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

    if redis:
        redis.hmset(rkey("t", msg.topic, "/status"), dict(status=msg.payload))

def on_voltage(mosq, userdata, msg):
    if msg.retain == 1 or len(msg.payload) < 0:
        return

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

    if redis is None:
        return

    device = msg.topic
    payload = msg.payload

    if device.endswith('/voltage/batt'):
        voltage = 'batt'
        device = device[:-len("/voltage/batt")]
        redis.hmset("t:" + device, dict(vbatt=payload))

        redis.lpush("vbatt:" + device, payload)
        redis.ltrim("vbatt:" + device, 0, MAX_VOLTAGES)
    else:
        voltage = 'ext'
        device = device[:-len("/voltage/ext")]
        redis.hmset("t:" + device, dict(vext=payload))

        redis.lpush("vext:" + device, payload)
        redis.ltrim("vext:" + device, 0, MAX_VOLTAGES)


def on_alarm(mosq, userdata, msg):
    if msg.retain == 1 or len(msg.payload) < 0:
        return

    save_rawdata(msg.topic, msg.payload)

    item = payload2location(msg.topic, msg.payload)
    if item is None or type(item) != dict:
        return

    watcher(mosq, msg.topic, item)
    if alarm_plugin is not None:
        try:
            alarm_plugin.alarmplugin(msg.topic, item, mosq)
        except Exception, e:
            print "NOPLUG ", e
            # logging.info("storage_plugin %s: %s" % (storage_plugin, e))


def on_start(mosq, userdata, msg):
    if msg.retain == 1 or len(msg.payload) < 0:
        return

    print "STARTUP ", msg.payload

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

    imei, version, tstamp = msg.payload.split(' ')

    if redis:
        redis.hmset(rkey("t", msg.topic, "/start"), {
                        'imei' : imei,
                        'version' : version,
                        'tstamp' : tstamp,
                        })

        # Register IMEI for lookups in otap.jad
        redis.set("imei:" + imei, "t:" + device_name(msg.topic, "/start"))




def on_gpio(mosq, userdata, msg):
    if msg.retain == 1 or len(msg.payload) < 0:
        return

    print "GPIO ", msg.payload

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

def on_operator_watch(mosq, userdata, msg):
    if msg.retain == 1 or len(msg.payload) < 0:
        return
    watcher(mosq, msg.topic, msg.payload)

def on_operator(mosq, userdata, msg):

    if msg.retain == 1 or len(msg.payload) < 1:
        return

    if cf.g('features', 'plmn', False) == False:
        return

    topic = msg.topic
    payload = str(msg.payload)

    watcher(mosq, topic, payload)

    try:
        o = payload.split()
        odata = {
            'topic'    : topic.replace("/operators", ""),
            'tst'      : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(time.time()))),
            'plmn'     : o[0],
            'extended' : " ".join(o[1:]),
        }

        op = Operators(**odata)
        op.save()
    except Exception, e:
        print "OPERATORS: ", str(e)

    save_rawdata(topic, payload)

    #try:
    #    f = open('operators.txt', 'a')
    #    s = "%d %s %s\n" % (int(time.time()), str(topic), payload)
    #    f.write(s)
    #    f.close()
    #except Exception, e:
    #    print "Can't write to operators.txt: ", str(e)

    try:
        for code in payload.split():
            code = code.replace('+', '')
            code = code.replace('-', '')
            code = code.replace('?', '')
            mcc = code[0:3]
            mnc = code[3:]

            cc = '??'
            try:
                cc = mobile_codes.mcc(mcc)[0]
                cc = cc.alpha2
            except:
                pass
    
            try:
                c = mobile_codes.mcc_mnc(mcc, mnc)
                s = "%s (%s)" % (str(c.brand), str(cc))
                mosq.publish(topic + "/" + code, s, qos=0, retain=False)
            except:
                s = "not found"
                mosq.publish(topic + "/" + code, s, qos=0, retain=False)
    except Exception, e:
        print "Cannot handle operators", str(e)

def payload2location(topic, payload):

    item = {}

    # Payloads are either JSON or CSP.
    try:
        item = json.loads(payload)
        if type(item) != dict:
            return None
    except ValueError:
        # eg: "K2,542A46AA,k,40365854,4575769,26,4,7,5,8"
        MILL = 1000000.0

        fieldnames = ['tid', 'tst', 't', 'lat', 'lon', 'cog', 'vel', 'alt', 'dist', 'trip' ]

        csvreader = csv.DictReader(io.StringIO(u(payload)), fieldnames=fieldnames)
        for r in csvreader:
            item = {
                '_type' : 'location',
                'tid'   : r.get('tid', '??'),
                'tst'   : int(r.get('tst', 0), 16),
                't'     : r.get('t', 'X'),
                'lat'   : float(float(r.get('lat')) / MILL),
                'lon'   : float(float(r.get('lon')) / MILL),
                'cog'   : int(r.get('cog', 0)) * 10,
                'vel'   : int(r.get('vel', 0)),
                'alt'   : int(r.get('alt', 0)) * 10,
                'dist'  : int(r.get('dist', 0)),
                'trip'  : int(r.get('trip', 0)) * 1000,
            }
            # print (json.dumps(item, sort_keys=True))
    except:
        return None

    if 'tid' not in item:
        item['tid'] = topic[-2:]
    if 't' not in item:
        item['t'] = '-'

    # Coerce numeric to types

    for elem in ['tst', 'cog', 'vel', 'alt', 'dist', 'trip']:
        item[elem] = int(item.get(elem, 0))
    for elem in ['lat', 'lon']:
        item[elem] = float(item.get(elem))

    return item

def watcher(mosq, topic, data):

    watcher_topic = cf.g('features', 'watcher', None)
    if watcher_topic is None:
        return

    time_format = "%d.%m %H:%M:%S"
    tstamp = datetime.datetime.fromtimestamp(int(time.time())).strftime(time_format)

    fmt = u"%-14s %-32s %s"

    if type(data) is not dict:
        s = fmt % (tstamp, topic, data)
        bb = bytearray(s.encode('utf-8'))
        mosq.publish(watcher_topic, bb, qos=0, retain=False)
        return

    time_str = None
    if '_type' in data:
        if data['_type'] == 'location':
            if 'tst' in data:
                tstamp = datetime.datetime.fromtimestamp(data['tst']).strftime(time_format)
            t   = data.get('t')
            tid = data.get('tid')
            cog = data.get('cog')
            vel = data.get('vel')
            vel = "%3d" % data.get('vel')
            alt = data.get('alt')
            trip = data.get('trip')
            dist = data.get('dist')
            lat = data.get('lat')
            lon = data.get('lon')
            addr = data.get('addr', '')

            loc = "%s,%s" % (lat, lon)
            s = "t=%s tid=%-2s c=%-3s v=%-6s a=%-6s trip=%-7s dist=%-5s loc=%-20s %s" % (
                    t, tid, cog, vel, alt, trip, dist, loc, addr
                )
            s = fmt % (tstamp, topic, s)
            bb = bytearray(s.encode('utf-8'))
            mosq.publish(watcher_topic, bb, qos=0, retain=False)
    else:
        s = fmt % (tstamp, topic, json.dumps(data))
        mosq.publish(watcher_topic, s, qos=0, retain=False)


def on_message(mosq, userdata, msg):
    
    types = ['location', 'waypoint']

    if msg.retain == 1:
        return

    topic = msg.topic
    payload = str(msg.payload)
    save_rawdata(topic, msg.payload)

    if len(msg.payload) < 1:
        return

    item = payload2location(topic, payload)
    if item is None or type(item) != dict:
        return

    if '_type' not in item or item['_type'] not in types:
        return
    if 'lat' not in item or 'lon' not in item:
        return

    try:
        sql_db.connect()
    except Exception, e:
        print str(e)


    tid = item.get('tid')
    tst = item.get('tst', int(time.time()))
    lat = item.get('lat')
    lon = item.get('lon')
    trip = item.get('trip', 0)
    dist = item.get('dist', 0)
    vel = item.get('vel', 0)


    t_ignore = cf.g('features', 't_store', [ 'p' ])
    if item['t'] in t_ignore:
        return

    item['topic'] = topic
    try:
        parts = topic.split('/')
        item['username'] = parts[1]
        item['device'] = parts[2]
    except:
        item['username'] = 'unknown'
        item['device'] = 'unknown'

    orig_tst = tst
    tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(tst))
    item['tst'] = tstamp

    if item['_type'] == 'waypoint':
        # FIXME: publish this as geofence for maps

        # Upsert
        try:
            sql_db.execute_sql("""
                  REPLACE INTO waypoint
                  (topic, username, device, tid, lat, lon, tst, rad, waypoint)
                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                  """, (
                      item['topic'], item['username'], item['device'], item['tid'], item['lat'],
                      item['lon'], tstamp, item['rad'], item['desc'],))
        except Exception, e:
            print("Cannot upsert waypoint in DB: %s" % (str(e)))

        return

    if item['_type'] != 'location':
        return

    item['ghash'] = None
    item['cc'] = None
    event_desc = "(%s, %s)" % (lat, lon)
    g = geo.rev(lat, lon, api='google')
    if g is not None:
        item['ghash'] = g.get('ghash')
        item['cc']    = g.get('cc', None)
        if 'addr' in g:
            event_desc = g.get('addr')
            item['addr'] = g.get('addr')
        print "%s %-2s %5d %s" % (g.get('cached', -1), tid, vel, g.get('addr', ''))
    else:
        print "  %-2s" % tid


    loca = Location(**item)
    loca.save()

    item['tst'] = orig_tst
    watcher(mosq, topic, item)

    # If this is a 'driving' report, add a key to Redis with expiry
    if redis and item.get('t') == 't':
        redis.hmset("driving:" + tid, {
                                        'tid'  : tid,
                                        'tst'  : tst,
                                        'trip' : trip,
                                        'vel'  : vel,
                                      }, SEEN_DRIVING)


    # Set position key in Redis to drive a map
    if redis:
        redis.hmset("lastloc:" + tid, {
                                    'lat' : lat,
                                    'lon' : lon,
                                    'tst' : orig_tst,
                                    }, LASTLOC_EXPIRY)

    # Record number of PUBs as metric
    if redis:
        redis.hincrby(rkey("t", msg.topic), "npubs", 1)


    # FIXME: handle geofence events (see https://github.com/owntracks/gw/issues/73 )

    eventdata = {
        'tid'       : tid,
        'event'     : "enter",  # leave
        'desc'      : event_desc,
        'tst'       : orig_tst,
    }
    event_topic = topic + "/event"

    # publish event_topic, json.dumps(eventdata)

m = cf.config('mqtt')
base_topics = list(m['base_topics'])

clientid = m.get('client_id', 'o2s-%s' % os.getpid())
mqttc = paho.Client(clientid, clean_session=True, userdata=None, protocol=paho.MQTTv31)
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_disconnect = on_disconnect

if m.get('username') is not None:
    mqttc.username_pw_set(m.get('username'), m.get('password'))

if m.get('ca_certs') is not None:   # use TLS
    tls_version = m.get('tls_version', 'tlsv1')

    if tls_version == 'tlsv1':
        tls_version = ssl.PROTOCOL_TLSv1
    if tls_version == 'sslv3':
        tls_version = ssl.PROTOCOL_SSLv3


    mqttc.tls_set(m.get('ca_certs'), tls_version=tls_version, ciphers=None)

    if m.get('tls_insecure') == True:
        mqttc.tls_insecure_set(True)


host = m.get('host', 'localhost')
port = int(m.get('port', 1883))
try:
    mqttc.connect(host, port, 60)
except Exception, e:
    sys.exit("Connect to `%s:%d': %s" % (host, port, str(e)))

for t in base_topics:
    mqttc.message_callback_add("%s/+/operators" % t, on_operator)
    if cf.g('features', 'plmn', False) == True:
        mqttc.message_callback_add("%s/+/operators/+" % t, on_operator_watch)
    mqttc.message_callback_add("%s/+/cmd/#" % t, on_cmd)
    mqttc.message_callback_add("%s/+/status" % t, on_status)
    mqttc.message_callback_add("%s/+/voltage/+" % t, on_voltage)
    mqttc.message_callback_add("%s/+/gpio/+" % t, on_voltage)
    mqttc.message_callback_add("%s/+/alarm" % t, on_alarm)
    mqttc.message_callback_add("%s/+/start" % t, on_start)


# FIXME: I must keep record of ../status up/down and their times

while True:
    try:
        mqttc.loop_forever()
    except socket.error:
        time.sleep(5)
    except KeyboardInterrupt:
        mqttc.disconnect()
        sys.exit(0)
    except:
        raise
