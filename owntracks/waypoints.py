#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import time
import datetime
import json
import os
import owntracks
from owntracks.dbschema import db, Waypoint
from geolocation import GeoLocation
import persist
import logging
import hashlib

log = logging.getLogger(__name__)

TRIGGER_ENTER   = 1
TRIGGER_LEAVE   = 0


class WP(object):
    def __init__(self, persistence_db, mosq, maptopic=None, alert_topic=None, alert_keys=None, watcher_topic=None):
        self.persistence_db = persistence_db
        self.mosq = mosq
        self.maptopic = maptopic
        self.watcher_topic = watcher_topic
        self.alert_topic = alert_topic
        self.alert_keys = []    # list of keys to add to JSON payload on fence alerts

        if alert_keys is not None:
            for elem in alert_keys.split():
                self.alert_keys.append(elem)

        self.tlist = persist.PersistentDict(self.persistence_db, 'c', format='pickle')
        self.wplist = self.load_waypoints()

        log.debug("alert_keys: {0}".format(self.alert_keys))

    def load_waypoints(self):

        wplist = []
        for w in Waypoint.select():
            try:
                lat     = float(w.lat)
                lon     = float(w.lon)
                meters  = int(w.rad)
                desc    = w.waypoint
                wptopic   = w.topic.replace('/waypoints', '')

                if meters == 0:
                    continue

                onepoint = WayPoint(lat, lon, meters, desc)
                wplist.append(onepoint)
                log.debug("Loading {0}".format(onepoint))

                if self.maptopic:
                    fence_data = {
                        '_type'    : 'fence',
                        'lat'      : lat,
                        'lon'      : lon,
                        'radius'   : meters,
                        'waypoint' : desc,
                    }
                    # I need a "key" to publish to maptopic so that one waypoint
                    # doesn't clobber the previous if both were originally to 
                    # same topic.

                    unique = "{0}-{1}-{2}".format(wptopic, lat, lon)
                    hash_object = hashlib.sha1(unique)
                    unique_sha = hash_object.hexdigest()

                    try:
                        # fence_topic = self.maptopic + "/" + unique_sha
                        fence_topic = self.maptopic.format(wptopic) + "/" + unique_sha
                        self.mosq.publish(fence_topic, json.dumps(fence_data), qos=0, retain=True)
                        log.debug("FENCE: {0} -> {1}".format(fence_topic, json.dumps(fence_data)))
                    except Exception, e:
                        log.warn("Cannot publish fence: {0}".format(str(e)))
            except:
                pass

        return wplist

    def alert(self, wp, trigger, item, meters, km):

        if self.alert_topic is None:
            return

        payload = {
                '_type'     : 'alert',
                'trigger'   : trigger,
                'meters'    : int(meters),
                'km'        : km,
                'wplat'     : wp.lat,
                'wplon'     : wp.lon,
                'wpname'    : wp.description,
            }

        if trigger == TRIGGER_ENTER:
            payload['event'] = 'enters'
        else:
            payload['event'] = 'leaves'

        key_list = self.alert_keys
        if key_list is None or len(key_list) == 0:
            key_list = list(item.keys())
        for key in key_list:
            if key in item:
                if key == '_type':
                    continue
                if key == 'topic':
                    payload['wptopic'] = item[key]
                else:
                    payload[key] = item[key]


        try:
            self.mosq.publish(self.alert_topic, json.dumps(payload, sort_keys=True), qos=0, retain=False)
        except Exception, e:
            log.warn("Cannot publish fence: {0}".format(str(e)))

        if self.watcher_topic is not None:
            # NOTE `tstamp' is UTC
            message = "ALERT: {tid}: {event} {wpname} at {tstamp}. Distance: {meters}m".format(**payload)
            log.info(message)
            print message
            try:
                self.mosq.publish(self.watcher_topic, message, qos=0, retain=False)
            except Exception, e:
                log.warn("Cannot publish fence: {0}".format(str(e)))


    def check(self, item):

        lat = item['lat']
        lon = item['lon']
        tid = item['tid']
        topic = item['topic']

        try:
            here = GeoLocation.from_degrees(lat, lon)
            for wp in self.wplist:
                trigger = None
                meters = 0
                try:
                    meters = here.distance_to(wp.point) * 1000.
                except:
                    pass

                km = "{:.2f}".format( float(meters / 1000.0) )

                movement = {
                    'km' : km,
                    'tid' : tid,
                    'topic' : topic,
                    'event' : None,
                }
                very_near = meters <= wp.meters
                if very_near is False:
                    if topic in self.tlist:
                        if self.tlist[topic] == wp:
                            trigger = TRIGGER_LEAVE
                            self.alert(wp, trigger, item, meters, km)

                            del self.tlist[topic]
                            self.tlist.sync()

                if very_near is True:
                    if topic not in self.tlist:
                        trigger = TRIGGER_ENTER
                        self.tlist[topic] = wp
                        self.tlist.sync()

                        self.alert(wp, trigger, item, meters, km)
                    else:
                        # Optional:
                        # msg = "%s STILL AT  %s (%s km)" % (topic, self.tlist[topic], km)
                        # print msg
                        return
        except:
            raise
            pass

class WayPoint(object):
    def __init__(self, lat, lon, meters=1000, description=None):
        self.lat = lat
        self.lon = lon
        self.meters = meters
        self.description = description

        self.point = GeoLocation.from_degrees(lat, lon)
        self.state = None

    def point(self):
        return self.point

    def __str__(self):
        return ("{0:s} ({1:.4f}, {2:.4f})").format(
                    self.description.encode('utf-8'), self.lat, self.lon)

    def __eq__(self, other):
        eq = False

        if self.lat == other.lat and \
            self.lon == other.lon:
            eq = True
        return eq

