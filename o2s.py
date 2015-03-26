#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import sys
import os
import logging
import time
import datetime
import owntracks
from owntracks import cf
from owntracks.revgeo import RevGeo
from owntracks.can2human import can2human
import paho.mqtt.client as paho
import ssl
import json
import socket
from owntracks import mobile_codes
from owntracks.dbschema import db, Location, Waypoint, RAWdata, Operators, Inventory, Job, Obd2, Fms, createalltables, dbconn, Lastloc
import io
import csv
import imp
from owntracks import waypoints
from owntracks.util import tsplit
import dateutil.parser
import tempfile
import codecs

sys.stdout = codecs.getwriter("utf-8")(sys.__stdout__) 

log = logging.getLogger(__name__)

SEEN_DRIVING = 1200
MAX_VOLTAGES = 10
LASTLOC_EXPIRY = 3600
MAX_JOBS = 16
INACTIVE_JOB = 0

storage = cf.g('features', 'storage', 'True')
maptopic = None
jobtopic = None
devices = {}
imeilist = {}
jobs = {}
jobnames = {}

createalltables()
jobnames[0] = ""

geo = RevGeo(cf.config('revgeo'), storage=storage)
wp = None

base_topics = []

alarm_plugin = None
if cf.g('features', 'alarm') is not None:
    try:
        alarm_plugin = imp.load_source('alarmplugin', cf.g('features', 'alarm'))
    except Exception, e:
        log.error("Can't import alarm_plugin {0}: {1}".format(storage_plugin, e))
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
    if not storage or cf.g('features', 'rawdata', False) == False:
        return

    try:
        rawdata = {
            'topic'  : topic,
            'tst'    : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(time.time()))),
            'payload' : payload,
        }
        rd = RAWdata(**rawdata)
        rd.save()
    except Exception, e:
        log.error("Cannot store rawdata for topic {0}: {1}".format(topic, str(e)))

def on_connect(mosq, userdata, rc):
    if rc != 0:
        log.error("Can't connect to MQTT. rc=={0}".format(rc))
        sys.exit(1)

    for t in base_topics:
        mqttc.subscribe("%s/+" % t, 0)
        mqttc.subscribe("%s/+/obd2/#" % t, 0)
        mqttc.subscribe("%s/+/fms/#" % t, 0)
        mqttc.subscribe("%s/+/waypoints" % t, 0)
        if cf.g('features', 'plmn', False) == True:
            mqttc.subscribe("%s/+/operators" % t, 0)
            mqttc.subscribe("%s/+/operators/+" % t, 0)
        mqttc.subscribe("%s/+/cmd/#" % t, 0)
        mqttc.subscribe("%s/+/alarm" % t, 0)
        mqttc.subscribe("%s/+/start" % t, 0)
        mqttc.subscribe("%s/+/status" % t, 0)
        mqttc.subscribe("%s/+/info" % t, 0)
        mqttc.subscribe("%s/+/voltage/+" % t, 0)
        mqttc.subscribe("%s/+/gpio/+" % t, 0)
        if cf.g('features', 'activo', False) == True:
            mqttc.subscribe("%s/+/proxy/jobs/+" % t, 0)

    if cf.o2smonitor:
        mqttc.subscribe(cf.o2smonitor + "/+", 2)

    log.info("Connected to and subscribed to MQTT broker")

def on_disconnect(mosq, userdata, rc):
    reasons = {
       '0' : 'Connection Accepted',
       '1' : 'Connection Refused: unacceptable protocol version',
       '2' : 'Connection Refused: identifier rejected',
       '3' : 'Connection Refused: server unavailable',
       '4' : 'Connection Refused: bad user name or password',
       '5' : 'Connection Refused: not authorized',
    }
    log.error("Disconnected: code={0} ({1})".format(rc, reasons.get(rc, 'unknown')))

def on_cmd(mosq, userdata, msg):
    if msg.retain == 1 or len(msg.payload) == 0:
        return

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

def device_name(topic, subtopic=None):
    ''' find base topic name from topic and subtopic. E.g. if
        topic == 'owntracks/gw/JP/start' and subtopic == '/start'
        return 'owntracks/gw/JP'
        '''

    base_topic, suffix = tsplit(topic)
    return base_topic

    #device = topic
    #if subtopic is not None:
    #    if device.endswith(subtopic):
    #        device = device[:-len(subtopic)]
    #return device


def push_map(mosq, device, device_data):
    ''' device is the original topic to which an update was published.
        device_data contains all we currently know of this device. If the
        data doesn't have a TID, do not publish as this means the object
        isn't yet complete, i.e. we don't yet know its position.
    '''

    if 'tid' not in device_data:
        log.debug("Object {0} is not yet complete.".format(device))
        return

    try:
        payload = json.dumps(device_data, sort_keys=True, separators=(',',':'))
    except Exception, e:
        log.error("Can't convert to JSON: {0}".format(str(e)))
        return

    try:
        if device.startswith('/'):
            device = device[1:]     # for Ben
        topic = maptopic.format(device)
        mosq.publish(topic, payload, qos=0, retain=True)
    except Exception, e:
        log.error("Cannot publish to maptopic at [{0}]: {1}".format(topic, str(e)))

def push_job(mosq, device, job_data):
    ''' device is the original topic to which an update was published.
        job_data contains all we currently know of this device. If the
        data doesn't have a TID, do not publish as this means the object
        isn't yet complete, i.e. we don't yet know its position.
    '''

    if 'tid' not in job_data:
        log.debug("Object {0} is not yet complete.".format(device))
        return

    try:
        payload = json.dumps(job_data, sort_keys=True, separators=(',',':'))
    except Exception, e:
        log.error("Can't convert to JSON: {0}".format(str(e)))
        return

    log.debug("Job payload: {0}".format(payload))

    try:
        if device.startswith('/'):
            device = device[1:]     # for Ben
        topic = jobtopic.format(device)
        mosq.publish(topic, payload, qos=0, retain=True)
    except Exception, e:
        log.error("Cannot publish to jobtopic at [{0}]: {1}".format(topic, str(e)))

def on_info(mosq, userdata, msg):
    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return

    device = str(msg.topic)
    if device.endswith('/info'):
        device = device[:-5]

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

    if maptopic:
        if device in devices:
            devices[device].update(dict(info=msg.payload))
            push_map(mosq, device, devices[device])


def on_status(mosq, userdata, msg):
    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return

    device = str(msg.topic)
    if device.endswith('/status'):
        device = device[:-7]

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

    if maptopic:
        if device in devices:
            status = -1
            try:
                status = int(msg.payload)
            except:
                pass
            devices[device].update(dict(status=status))
        else:
            try:
                devices[device] = dict(status=int(msg.payload))
            except:
                devices[device] = dict(status=-1)
        push_map(mosq, device, devices[device])


def on_voltage(mosq, userdata, msg):
    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return

    if not storage:
        return

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

    basetopic, suffix = tsplit(msg.topic)
    key = basetopic.split('/')[-1]      # IMEI or TID

    vext = vbatt = None
    if suffix.endswith('voltage/ext'):
        try:
            vext = float(msg.payload)
            if basetopic in devices:
                devices[basetopic].update(dict(vext=vext))
        except:
            return

    if suffix.endswith('voltage/batt'):
        try:
            vbatt = float(msg.payload)
            if basetopic in devices:
                devices[basetopic].update(dict(vbatt=vbatt))
        except:
            return

    try:
        inv = Inventory.select().where(
                (Inventory.imei == key) | (Inventory.tid == key)
           ).get()
        try:
            if vext is not None:
                inv.vext = vext
            if vbatt is not None:
                inv.vbatt = vbatt
            inv.tstamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            inv.save()
        except Exception, e:
            raise
            log.error("DB error on UPDATE Inventory in voltage: {0}".format(str(e)))
    except Inventory.DoesNotExist:
            pass
    except Exception, e:
        raise
        log.error("DB error on GET Inventory: {0}".format(str(e)))
        return


def on_alarm(mosq, userdata, msg):
    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return

    save_rawdata(msg.topic, msg.payload)

    item = payload2location(msg.topic, msg.payload)
    if item is None or type(item) != dict:
        return

    item['cc']   = '??'
    item['addr'] = 'unknown location'
    try:
        g = geo.rev(item.get('lat'), item.get('lon'), api='google')
        if g is not None:
            item['ghash'] = g.get('ghash')
            item['cc']    = g.get('cc', None)
            if 'addr' in g:
                item['addr'] = g.get('addr')
    except:
        pass

    watcher(mosq, msg.topic, item)
    if alarm_plugin is not None:
        try:
            alarm_plugin.alarmplugin(msg.topic, item, mosq)
        except Exception, e:
            log.error("Can't invoke alarm plugin with topic {0}: {1}".format(topic, str(e)))


def on_obd2(mosq, userdata, msg):
    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return

    if not storage:
        return

    basetopic, suffix = tsplit(msg.topic)

    args = suffix.split('/')    # ['obd2', '000007e8', '01', '49']

    canid = args[1]
    mode  = args[2]
    pid   = None
    if len(args) > 3:
        pid = args[3]

    log.debug("_obd2: {0} {1}".format(msg.topic, msg.payload))
    watcher(mosq, msg.topic, msg.payload)
    try:
        data = {
            'topic'  : msg.topic,
            'tst'    : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(time.time()))),
            'payload' : msg.payload,
            'canid'   : canid,
            'mode'    : mode,
            'pid'     : pid,
        }
        ob = Obd2(**data)
        ob.save()
    except Exception, e:
        log.error("Cannot store OBD2 for topic {0}: {1}".format(msg.topic, str(e)))

def on_fms(mosq, userdata, msg):
    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return

    if not storage:
        return

    basetopic, suffix = tsplit(msg.topic)

    log.debug("_fms: {0} {1}".format(msg.topic, msg.payload))
    watcher(mosq, msg.topic, msg.payload)
    try:
        data = {
            'topic'  : msg.topic,
            'tst'    : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(time.time()))),
            'payload' : msg.payload,
        }
        fm = Fms(**data)
        fm.save()
    except Exception, e:
        log.error("Cannot store FMS for topic {0}: {1}".format(msg.topic, str(e)))


def on_start(mosq, userdata, msg):
    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return

    log.debug("_start: {0} {1}".format(msg.topic, msg.payload))

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

    imei = version = ""
    try:
        imei, version, tstamp = msg.payload.split(' ')
    except:
        log.error("Cannot split() on ../start")
        return

    startup_dt = None
    try:
        startup_dt = dateutil.parser.parse(tstamp)
    except:
        startup_dt = datetime.datetime.now()

    # Inventory must have base topic in it so that we can later associate TID
    # with the IMEI

    basetopic, suffix = tsplit(msg.topic)

    odo = 0
    try:
        inv = Inventory.get(Inventory.imei == imei)
        odo = int(inv.odo)

        try:
            inv.topic = basetopic
            inv.version = version
            inv.startup = startup_dt
            try:
                if basetopic in devices:
                    inv.tid = devices[basetopic]['tid']
            except:
                pass
            inv.tstamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            inv.save()
        except Exception, e:
            raise
            log.error("DB error on UPDATE Inventory: {0}".format(str(e)))
    except Inventory.DoesNotExist:
        try:
            inv = Inventory(topic=basetopic, imei=imei, version=version, startup=startup_dt)
            if basetopic in devices:
                inv.tid = devices[basetopic]['tid']
            inv.save()
        except Exception, e:
            log.error("DB error on SAVE Inventory: {0}".format(str(e)))
    except Exception, e:
        raise
        log.error("DB error on GET Inventory: {0}".format(str(e)))
        return

    if maptopic:
        if basetopic in devices:
            devices[basetopic].update(dict(odo=odo, imei=imei, version=version))
        else:
            try:
                devices[basetopic] = dict(odo=odo, imei=imei, version=version)
            except:
                devices[basetopic] = dict(odo=odo, imei=imei, version=version)
        push_map(mosq, basetopic, devices[basetopic])

def on_gpio(mosq, userdata, msg):
    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return

    log.debug("_gpio: {0} {1}".format(msg.topic, msg.payload))

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

def on_job(mosq, userdata, msg):
    # ignore if 'activo' hasn't been enabled
    if cf.g('features', 'activo', False) == False:
        return

    # topic owntracks/gw/B2/proxy/jobs/[active|<jobid>]
    base_topic, suffix = tsplit(msg.topic)

    parts = suffix.split('/')
    last_part = parts[len(parts) - 1]

    # suffix proxy/jobs/[active|<jobid>]
    if last_part == 'active':
        # handle this active job change event
        on_activejob(mosq, msg, base_topic)
    else:
        # update the job name list
        jobnames[int(last_part)] = msg.payload

def on_activejob(mosq, msg, device):
    # ignore retained 'active' messages (assume we have already processed)
    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return

    log.debug("_job: {0} {1}".format(msg.topic, msg.payload))

    save_rawdata(msg.topic, msg.payload)
    watcher(mosq, msg.topic, msg.payload)

    # initialise our job list    
    if device not in jobs:
        jobs[device] = dict(topic=device)
  
    # update the tid from our map data
    tid = '??'
    if device in devices and 'tid' in devices[device]:
        tid = devices[device]['tid']
        jobs[device].update(dict(tid=tid))

    now = int(time.time())
    nowstr = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now))

    # extract the job id
    job = int(msg.payload)

    # calculate the job metadata
    jobname = None
    jobduration = None
    if job == INACTIVE_JOB:
        if 'jobstart' in jobs[device] and jobs[device]['jobstart'] != None:
            jobduration = now - jobs[device]['jobstart']
    else:
        if job in jobnames:
            jobname = jobnames[job]
        else:
            jobname = msg.payload

    # update the job parameters in our map display
    if maptopic:
        if device in devices:
            devices[device].update(dict(job=job, jobname=jobname))
            push_map(mosq, device, devices[device])

    # update the job topic
    if jobtopic:
        if device in jobs:
            if job == INACTIVE_JOB:
                jobs[device].update(dict(jobend=now, jobduration=jobduration))
            else:
                jobs[device].update(dict(job=job, jobname=jobname, jobstart=now, jobend=None, jobduration=None))
            if 'jobstart' in jobs[device]:
                push_job(mosq, device, jobs[device])

    if storage:
        if job == INACTIVE_JOB:
            try:
                jb = Job.get(Job.topic == device, Job.end == None)
                jb.end = nowstr
                jb.save()
            except Job.DoesNotExist:
                log.error("Received 'end' event for job with no active row")
            except Exception, e:
                raise
                log.error("DB error on UPDATE Job: {0}".format(str(e)))
  
        else:
            try:
                data = {
                    'topic'   : device,
                    'tid'     : tid,
                    'job'     : job,
                    'jobname' : jobname,
                    'start'   : nowstr,
                }
                jb = Job(**data)
                jb.save()
            except Exception, e:
                log.error("Cannot store JOB for topic {0}: {1}".format(msg.topic, str(e)))
 
def on_operator_watch(mosq, userdata, msg):
    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return
    watcher(mosq, msg.topic, msg.payload)

def on_operator(mosq, userdata, msg):

    if (skip_retained and msg.retain == 1) or len(msg.payload) == 0:
        return

    if cf.g('features', 'plmn', False) == False:
        return

    topic = msg.topic
    payload = str(msg.payload)

    watcher(mosq, topic, payload)

    if storage:
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
            log.error("Can't store operators in DB: {0}".format(str(e)))

    save_rawdata(topic, payload)

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
        log.error("Can't handle operators: {0}".format(str(e)))

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

        try:
            csvreader = csv.DictReader(io.StringIO(u(payload)), fieldnames=fieldnames)
            for r in csvreader:
                item = {
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
        except Exception, e:
            log.error("CSV decoding fails for {0}: {1}".format(topic, str(e)))
            return None
    except:
        log.error("Payload decoding fails for {0}: {1}".format(topic, str(e)))
        return None

    if 'tid' not in item:
        item['tid'] = topic[-2:]
    if 't' not in item:
        item['t'] = '-'

    # Coerce numeric to types

    for elem in ['tst', 'cog', 'vel', 'alt', 'dist', 'trip']:
        item[elem] = int(item.get(elem, 0))
    for elem in ['lat', 'lon']:
        try:
            item[elem] = float(item.get(elem))
        except:
            pass

    return item

# WATCHER
def watcher(mosq, topic, data):

    watcher_topic = cf.g('features', 'watcher', None)
    if watcher_topic is None:
        return

    try:
        prefix, suffix = tsplit(topic)
        wt = watcher_topic.format(prefix) + "/" + suffix
    except Exception, e:
        log.error("Cannot format watcher_topic: {0}".format(str(e)))
        return

    time_format = "%d.%m %H:%M:%S"
    tstamp = datetime.datetime.fromtimestamp(int(time.time())).strftime(time_format)

    fmt = u"%-14s %-32s %s"

    if type(data) is not dict:
	human = can2human(str(topic), str(data))

	if human != None:
		s = fmt % (tstamp, topic, human)
		bb = bytearray(s.encode('utf-8'))
		mosq.publish(wt, bb, qos=0, retain=False)
		return
	else:
		s = fmt % (tstamp, topic, data)
		bb = bytearray(s.encode('utf-8'))
		mosq.publish(wt, bb, qos=0, retain=False)
		return

    time_str = None

    # FIXME: support waypoint, alarm and alert
    if 'tst' in data:
        tstamp = datetime.datetime.fromtimestamp(data['tst']).strftime(time_format)
    t   = data.get('t')
    tid = data.get('tid')
    cog = data.get('cog')
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
    mosq.publish(wt, bb, qos=0, retain=False)


def on_message(mosq, userdata, msg):
    
    if (skip_retained and msg.retain == 1):
        return

    topic = msg.topic

    if len(msg.payload) == 0:
        '''
        Clear out everthing we know of this vehicle?
        We cannot delete our own MQTT topics, because that'll result in a loop.
        '''

        # FIXME: we should subscribe to topic/# to find 'em all...
        # for s in ['status', 'start', 'gpio', 'voltage', 'operators', 'info']:
        #     mosq.publish("%s/%s" % (topic, s), None, qos=2, retain=True)
        # mosq.publish(topic, None, qos=2, retain=True)
        # mosq.publish(maptopic + "/" + topic, None, qos=2, retain=True)

        return


    payload = str(msg.payload)
    save_rawdata(topic, msg.payload)

    if len(msg.payload) < 1:
        return

    item = payload2location(topic, payload)
    if item is None or type(item) != dict:
        return

    if 'lat' not in item or 'lon' not in item:
        return

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

    orig_tst = tst
    tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(tst))
    item['tst'] = tstamp

    if storage:
        try:
            dbconn()
        except Exception, e:
            log.error("Reconnect to DB: {0}".format(str(e)))
            return

    item['ghash'] = None
    item['cc']    = '??'
    item['addr']  = 'unknown location'
    event_desc = "(%s, %s)" % (lat, lon)
    g = geo.rev(lat, lon, api='google')
    if g is not None:
        item['ghash'] = g.get('ghash')
        item['cc']    = g.get('cc', None)
        if 'addr' in g:
            event_desc = g.get('addr')
            item['addr'] = g.get('addr')
            addr = g.get('addr')
        print "%s %-2s %5d %s [%s] %s,%s" % (g.get('cached', -1), tid, vel, addr, item.get('ghash'), item.get('lat'), item.get('lon'))
    else:
        print "  %-2s" % tid


    if storage:
        try:
            loca = Location(**item)
            loca.save()
        except Exception, e:
            log.error("Cannot INSERT location for {0} into DB: {1}".format(topic, str(e)))

        # Upsert last vehicle location into Lastloc
        try:
            ll = Lastloc.get(Lastloc.topic == topic)
            ll.tid     = item.get('tid')
            ll.lat     = item.get('lat')
            ll.lon     = item.get('lon')
            ll.tst     = item.get('tst')
            ll.vel     = item.get('vel')
            ll.alt     = item.get('alt')
            ll.cog     = item.get('cog')
            ll.trip    = item.get('trip')
            ll.dist    = item.get('dist')
            ll.t       = item.get('t')
            ll.ghash   = item.get('ghash')
            ll.cc      = item.get('cc')
            ll.save()

        except Lastloc.DoesNotExist:
            try:
                ll = Lastloc(**item)
                ll.save()
            except Exception, e:
                log.error("Cannot INSERT lastloc into DB: {0}".format(str(e)))
        except Exception, e:
            log.error("Cannot UPSERT location into DB: {0}".format(str(e)))



    item['tst'] = orig_tst
    watcher(mosq, topic, item)

    compass = '-'
    points = [ 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N' ]
    if item.get('cog') is not None:
        cog = int(item.get('cog', 0))
        idx = int(cog / 45)
        compass = points[idx]

    new_data = {
            'tid'     : tid,
            'lat'     : lat,
            'lon'     : lon,
            'cog'     : item.get('cog', 0),
            'vel'     : item.get('vel', 0),
            'alt'     : item.get('alt', 0),
            'dstamp'  : time.strftime('%d/%H:%M:%S', time.localtime(orig_tst)), # display in Tables
            'tstamp'  : time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(orig_tst))),
            'compass' : compass,
            'addr'    : item.get('addr'),
            'cc'      : item.get('cc'),
            'status'  : 1,      # Safe to assume it's "online" if we get position
            'topic'   : topic,
            'tst'     : orig_tst,
            't'       : item.get('t', '-'),
            'trip'    : item.get('trip'),
            'dist'    : item.get('dist'),
        }
    # Republish to map.
    if maptopic:
        try:
            devices[topic].update(new_data)
        except KeyError:
            devices[topic] = new_data
        push_map(mosq, topic, devices[topic])

    # Geofence events
    if wp:
        try:
            wp.check(new_data)
        except Exception, e:
            log.error("Cannot check waypoint: {0}".format(str(e)))


def t_ghash(rest, val):
    ''' val must be TID=width (eg J4=8 or K2=4). Set ghash width for this TID '''
    pass

def t_loglevel(rest, val):
    ''' val is "INFO" or "DEBUG". Setting logging accordingly '''
    
    log.debug("t_loglevel: debug")
    log.info("t_loglevel: info")
    log.warning("t_loglevel: warning")

    newlevel = None
    try:
        newlevel = getattr(logging, val.upper())
        if not isinstance(newlevel, int):
            raise ValueError("Invalid log level")
    except:
        return "Unchanged"

    if newlevel is not None:
        cf.loglevelnumber = newlevel
        log.setLevel(cf.loglevelnumber)

        pw = logging.getLogger('peewee')
        pw.setLevel(cf.loglevelnumber)

    log.debug("t_loglevel: DEBUG")
    log.info("t_loglevel: INFO")
    log.warning("t_loglevel: WARNING")

    return "thanks"

def t_dump(rest, val):
    ''' val is string of what to dump. Write to file, return tmp filename '''

    if val == 'devices':
        s = json.dumps(devices, indent=2)

        f = tempfile.NamedTemporaryFile(prefix="o2s-devicedump-", suffix=".json", delete=False)
        filename = f.name
        f.write(s)
        f.close()

        log.info("t_dump: devices dumped to {0}".format(filename))
        return filename

    return "NAK: unknown dump subcommand"


def t_info(rest, val):
    ''' val is a tid. Show information of this TID from list of devices '''
    
    resp = ''

    tid = val
    for dev in devices:
        if 'tid' in devices[dev] and devices[dev]['tid'] == tid:
            return json.dumps(devices[dev])

    return "TID {0} not found".format(tid)

def t_imei(rest, val):
    ''' val is a TID. Return IMEI from Inventory '''

    tid = val
    resp = 'unknown TID=%s' % tid

    try:
        inv = Inventory.get(Inventory.tid == tid)
        resp = "TID={0} IMEI={1} topic={2}".format(inv.tid, inv.imei, inv.topic)
    except Inventory.DoesNotExist:
        log.warning("IMEI for TID={0} requested but not found".format(tid))
        pass
    except Exception, e:
        log.error("DB error on GET Inventory: {0}".format(str(e)))
        pass

    return resp


def on_tell(mosq, userdata, msg):
    if msg.retain == 1 or len(msg.payload) == 0:
        return

    dispatch_table = {
        #FIXME 'ghash'     : t_ghash,      # _owntracks/o2s/ghash    K2=5
        'loglevel'  : t_loglevel,   # _owntracks/o2s/loglevel INFO
        'dump'      : t_dump,       # _owntracks/o2s/dump     devices
        'info'      : t_info,       # _owntracks/o2s/info     tid
        'imei'      : t_imei,       # _owntracks/o2s/imei     tid
        }

    payload = msg.payload

    orig_topic = msg.topic
    topic, cmd = tsplit(msg.topic, 2)  # "_owntracks/o2s/+"

    if cmd in dispatch_table:
        result = None
        try:
            result = dispatch_table[cmd]("xxx", payload)
        except Exception, e:
            result = "Tell: cmd {0} with val {1} failed: {2}".format(cmd, payload, str(e))
            log.error(result)
        bb = bytearray(result.encode('utf-8'))
        mosq.publish(orig_topic + '/out', bb, qos=2, retain=False)
    else:
        log.info("Illegal cmd {0} received".format(cmd))
        mosq.publish(orig_topic + '/out', "NAK", qos=2, retain=False)

    return


m = cf.config('mqtt')
base_topics = list(m['base_topics'])

clientid = m.get('client_id', 'o2s-{0}'.format(os.getpid()))
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


maptopic = m.get('maptopic', None)
jobtopic = m.get('jobtopic', None)
skip_retained = m.get('skip_retained', False)
host = m.get('host', 'localhost')
port = int(m.get('port', 1883))
try:
    mqttc.connect(host, port, 60)
except Exception, e:
    sys.exit("Connect to `%s:%d': %s" % (host, port, str(e)))

for t in base_topics:
    mqttc.message_callback_add("{0}/+/operators".format(t), on_operator)
    if cf.g('features', 'plmn', False) == True:
        mqttc.message_callback_add("{0}/+/operators/+".format(t), on_operator_watch)

    mqttc.message_callback_add("{0}/+/cmd/#".format(t), on_cmd)
    mqttc.message_callback_add("{0}/+/status".format(t), on_status)
    mqttc.message_callback_add("{0}/+/info".format(t), on_info)
    mqttc.message_callback_add("{0}/+/voltage/+".format(t), on_voltage)
    mqttc.message_callback_add("{0}/+/gpio/+".format(t), on_gpio)
    mqttc.message_callback_add("{0}/+/alarm".format(t), on_alarm)
    mqttc.message_callback_add("{0}/+/start".format(t), on_start)
    mqttc.message_callback_add("{0}/+/obd2/#".format(t), on_obd2)
    mqttc.message_callback_add("{0}/+/fms/#".format(t), on_fms)

    if cf.g('features', 'activo', False) == True:
        mqttc.message_callback_add("{0}/+/proxy/jobs/+".format(t), on_job)

    if cf.o2smonitor:
        mqttc.message_callback_add(cf.o2smonitor + "/+", on_tell)


# FIXME: I must keep record of ../status up/down and their times

geofences = cf.g('features', 'geofences', None)
if geofences is not None:
    alert_topic = cf.g('mqtt', 'alert_topic', None)
    alert_keys  = cf.g('mqtt', 'alert_keys', None)
    watcher_topic = cf.g('features', 'watcher', None)
    wp = waypoints.WP(geofences, mqttc, maptopic=maptopic, alert_topic=alert_topic, alert_keys=alert_keys, watcher_topic=watcher_topic)

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
