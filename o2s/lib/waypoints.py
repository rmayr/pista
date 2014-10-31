#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'

import time
import datetime
import json
import os
from dbschema import Waypoint, sql_db
from geolocation import GeoLocation
import persist
import logging

class WP(object):
    def __init__(self, persistence_db, mosq, maptopic=None):
        self.persistence_db = persistence_db
        self.mosq = mosq
        self.maptopic = maptopic

        self.tlist = persist.PersistentDict(self.persistence_db, 'c', format='pickle')
        self.wplist = self.load_waypoints()

    def load_waypoints(self):

        wplist = []
        for w in Waypoint.select():
            try:
                lat     = float(w.lat)
                lon     = float(w.lon)
                meters  = int(w.rad)
                desc    = w.waypoint
                wptopic   = w.topic

                if meters == 0:
                    continue

                onepoint = WayPoint(lat, lon, meters, desc)
                wplist.append(onepoint)

                if self.maptopic:
                    fence_data = {
                        '_type'    : 'fence',
                        'lat'      : lat,
                        'lon'      : lon,
                        'radius'   : meters,
                        'waypoint' : desc,
                    }
                try:
                    fence_topic = self.maptopic + "/" + wptopic
                    self.mosq.publish(fence_topic, json.dumps(fence_data), qos=0, retain=True)
                except Exception, e:
                    logging.warn("Cannot publish fence: %s" % (str(e)))
            except:
                pass

        return wplist

    def check(self, item):

        lat = item['lat']
        lon = item['lon']
        tid = item['tid']
        topic = item['topic']

        try:
            here = GeoLocation.from_degrees(lat, lon)
            for wp in self.wplist:
                meters = 0
                try:
                    meters = here.distance_to(wp.point) * 1000.
                except:
                    pass

                km = "%.2f" % float(meters / 1000.0)

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
                            movement['event'] = 'leave'
                            movement['location'] = str(self.tlist[topic])

                            msg = "%s ↜ LEAVES  %s (%s km)" % (topic, self.tlist[topic], km)
                            print msg

                            # alert(mosq, movement)
                            del self.tlist[topic]
                            self.tlist.sync()

                if very_near is True:
                    if topic not in self.tlist:
                        self.tlist[topic] = wp
                        self.tlist.sync()
                        movement['event'] = 'enter'
                        movement['location'] = str(self.tlist[topic])
                        msg = "%s ⇉ ENTERS  %s (%s km)" % (topic, self.tlist[topic], km)
                        print msg
                        # alert(mosq, movement)
                    else:
                        # Optional:
                        msg = "%s STILL AT  %s (%s km)" % (topic, self.tlist[topic], km)
                        print msg
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

