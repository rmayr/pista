#!/usr/bin/env python

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

from peewee import *
from owntracks import cf
import datetime
import os
import sys
import logging

log = logging.getLogger(__name__)

db = None

engines = {
    'postgresql' : PostgresqlDatabase(cf.dbname,
                        user=cf.dbuser,
                        password=cf.dbpasswd,
                        host=cf.dbhost,
                        port=cf.dbport,
                        threadlocals=True),
    'mysql'      : MySQLDatabase(cf.dbname,
                        user=cf.dbuser,
                        passwd=cf.dbpasswd,
                        host=cf.dbhost,
                        port=cf.dbport,
                        threadlocals=True),
    'sqlite'     : SqliteDatabase(cf.dbpath,
                        threadlocals=True),
}

if cf.dbengine in engines:
    db = engines[cf.dbengine]
else:
    raise ValueError("Configuration error: there is no database engine called `{0}'".format(cf.dbengine))


class OwntracksModel(Model):

    class Meta:
        database = db

class Geo(OwntracksModel):
    ghash           = CharField(null=False, max_length=8, unique=True)
    src             = IntegerField(null=True)       # source of reverse geo
    cc              = CharField(null=True, max_length=2)
    addr            = CharField(null=False)

class Location(OwntracksModel):
    topic           = CharField(null=False)
    tid             = CharField(null=False, max_length=2)
    lat             = DecimalField(null=False, max_digits=10, decimal_places=7)
    lon             = DecimalField(null=False, max_digits=10, decimal_places=7)
    tst             = DateTimeField(default=datetime.datetime.now, index=True)
    vel             = IntegerField(null=True)
    alt             = IntegerField(null=True)
    cog             = IntegerField(null=True)
    trip            = IntegerField(null=True)
    dist            = IntegerField(null=True)
    t               = CharField(null=True, max_length=1)
    ghash           = CharField(null=True, max_length=8)
    cc              = CharField(null=True, max_length=2)

    class Meta:
        indexes = (
            # Create non-unique on tid
            (('tid', ), False),
            (('topic', ), False),  # create index l_topic on location(topic (100));
        )

# Last reported location per topic (topic is unique)
class Lastloc(OwntracksModel):
    topic           = CharField(null=False, unique=True)
    tid             = CharField(null=False, max_length=2)
    lat             = DecimalField(null=False, max_digits=10, decimal_places=7)
    lon             = DecimalField(null=False, max_digits=10, decimal_places=7)
    tst             = DateTimeField(default=datetime.datetime.now, index=True)
    vel             = IntegerField(null=True)
    alt             = IntegerField(null=True)
    cog             = IntegerField(null=True)
    trip            = IntegerField(null=True)
    dist            = IntegerField(null=True)
    t               = CharField(null=True, max_length=1)
    ghash           = CharField(null=True, max_length=8)
    cc              = CharField(null=True, max_length=2)

class Job(OwntracksModel):
    topic           = CharField(null=False)
    tid             = CharField(null=False, max_length=2)
    job             = IntegerField(null=False)
    jobname         = CharField(null=True, max_length=20)
    start           = DateTimeField(default=datetime.datetime.now, index=True)
    end             = DateTimeField(null=True)
    duration        = IntegerField(null=True)

    class Meta:
        indexes = (
            # When a job ends we look up using tid and null end
            (('tid', ), False),
            (('end', ), False),
        )
 
class RAWdata(OwntracksModel):
    topic           = CharField(null=False)
    tst             = DateTimeField(default=datetime.datetime.now, index=True)
    payload         = TextField(null=True)

class Obd2(OwntracksModel):
    topic           = CharField(null=False)
    tst             = DateTimeField(default=datetime.datetime.now, index=True)
    canid           = CharField(null=True) # CAN ID
    mode            = CharField(null=True)
    pid             = CharField(null=True) # Parameter ID
    payload         = TextField(null=True)

class Fms(OwntracksModel):
    topic           = CharField(null=False)
    tst             = DateTimeField(default=datetime.datetime.now, index=True)
    payload         = TextField(null=True)

# Optional: operators. Useful for Greenwich only
class Operators(OwntracksModel):
    topic           = CharField(null=False)
    tst             = DateTimeField(default=datetime.datetime.now, index=True)
    plmn            = CharField(null=True, max_length=8)
    extended        = CharField(null=True)

class Waypoint(OwntracksModel):
    topic           = CharField(null=False)
    tid             = CharField(null=False, max_length=2)
    lat             = DecimalField(null=False, max_digits=10, decimal_places=7)
    lon             = DecimalField(null=False, max_digits=10, decimal_places=7)
    tst             = DateTimeField(default=datetime.datetime.now)
    rad             = IntegerField(null=True)
    waypoint        = CharField(null=True)

    class Meta:
        indexes = (
            # Create a unique index on tst
            (('tst', ), True),
        )


class User(OwntracksModel):
    username        = CharField(null=False, unique=True)
    pwhash          = CharField(null=False)
    superuser       = IntegerField(null=False)
    org             = IntegerField(null=True)
    token           = CharField(null=True)
    note            = CharField(null=True)
    tstamp          = DateTimeField(default=datetime.datetime.now)


class Acl(OwntracksModel):
    username        = CharField(null=False)
    topic           = CharField(null=False)
    rw              = IntegerField(null=False)
    note            = CharField(null=True)
    tstamp          = DateTimeField(default=datetime.datetime.now)

    class Meta:
        indexes = (
            # Create unique on username, topic
            (('username', 'topic'), True),
        )

class Params(OwntracksModel):
    org             = ForeignKeyField(User)
    name            = CharField(null=True)
    host            = CharField(null=True)
    port            = IntegerField(null=True)
    tls             = IntegerField(null=True)
    auth            = IntegerField(null=True)
    mqttuser        = CharField(null=True)
    mqttpass        = CharField(null=True)
    certurl         = CharField(null=True)
    trackurl        = CharField(null=True)


class Inventory(OwntracksModel):
    topic           = CharField(null=False)
    imei            = CharField(null=False, max_length=15, unique=True)
    tid             = CharField(null=True, max_length=2)
    version         = CharField(null=True, max_length=10)
    startup         = DateTimeField(null=True)
    odo             = DecimalField(null=False, max_digits=7, decimal_places=0, default=0)
    vbatt           = DecimalField(null=True, max_digits=4, decimal_places=1, default=0)
    vext            = DecimalField(null=True, max_digits=4, decimal_places=1, default=0)
    label           = CharField(null=True)
    tstamp          = DateTimeField(default=datetime.datetime.now)

    class Meta:
        indexes = (
        )

def createalltables():

    silent = True

    db.connect()

    Location.create_table(fail_silently=silent)
    Lastloc.create_table(fail_silently=silent)
    Waypoint.create_table(fail_silently=silent)
    Geo.create_table(fail_silently=silent)
    User.create_table(fail_silently=silent)
    Acl.create_table(fail_silently=silent)
    Inventory.create_table(fail_silently=silent)
    Params.create_table(fail_silently=silent)
    Obd2.create_table(fail_silently=silent)
    Fms.create_table(fail_silently=silent)

    if cf.g('features', 'plmn', False) == True:
        try:
            Operators.create_table(fail_silently=silent)
        except Exception, e:
            print str(e)

    if cf.g('features', 'rawdata', False) == True:
        try:
            RAWdata.create_table(fail_silently=silent)
        except Exception, e:
            print str(e)

    if cf.g('features', 'activo', False) == True:
        try:
            Job.create_table(fail_silently=silent)
        except Exception, e:
            print str(e)

def dbconn():
    # Attempt to connect if not already connected. For MySQL, take care of MySQL 2006
    try:
        db.connect()
    except Exception, e:
        log.info("Cannot connect to database: %s" % (str(e)))
