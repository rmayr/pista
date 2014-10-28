#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'

import time
import datetime
import json
import os
from dbschema import Waypoint, sql_db


def load_waypoints():

    for w in Waypoint.select():
        dbid    = w.id
        lat     = float(w.lat)
        lon     = float(w.lon)

        print lat, w.username, w.device, w.waypoint

