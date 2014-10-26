#!/usr/bin/env python

from peewee import *
from cf import conf
import datetime
import os
import sys

cf = conf(os.getenv('WAPPCONFIG', 'o2s.conf'))

sql_db = None
if (cf.g('database', 'dbengine', 'mysql') == 'postgresql'):
    # Use PostreSQL configuration
    sql_db = PostgresqlDatabase(cf.g('database', 'dbname', 'owntracks'),
        user=cf.g('database', 'dbuser'),
        port=cf.g('database', 'dbport', 5432),
        threadlocals=True)
else:
    sql_db = MySQLDatabase(cf.g('database', 'dbname', 'owntracks'),
        user=cf.g('database', 'dbuser'),
        passwd=cf.g('database', 'dbpasswd'),
        host=cf.g('database', 'dbhost', 'localhost'),
        port=cf.g('database', 'dbport', 3306),
        threadlocals=True)


class OwntracksModel(Model):

    class Meta:
        database = sql_db

class Location(OwntracksModel):
    topic           = BlobField(null=False)
    username        = CharField(null=False)
    device          = CharField(null=False)
    tid             = CharField(null=False, max_length=2)
    lat             = DecimalField(null=False, max_digits=10, decimal_places=7)
    lon             = DecimalField(null=False, max_digits=10, decimal_places=7)
    tst             = DateTimeField(default=datetime.datetime.now, index=True)
    # acc             = DecimalField(null=True, max_digits=6, decimal_places=1)
    # batt            = DecimalField(null=True, max_digits=3, decimal_places=1)
    # waypoint        = TextField(null=True)  # desc in JSON, but desc is reserved SQL word
    # event           = CharField(null=True)
    vel             = IntegerField(null=True)
    alt             = IntegerField(null=True)
    cog             = IntegerField(null=True)
    trip            = IntegerField(null=True)
    dist            = IntegerField(null=True)
    t               = CharField(null=True, max_length=1)
    ghash           = CharField(null=True, max_length=6)
    cc              = CharField(null=True, max_length=2)

    class Meta:
        indexes = (
            # Create non-unique on username, device
            (('username', 'device'), False),

            # Create non-unique on tid
            (('tid', ), False),
        )

class RAWdata(OwntracksModel):
    topic           = BlobField(null=False)
    tst             = DateTimeField(default=datetime.datetime.now, index=True)
    payload         = TextField(null=True)

# Optional: operators. Useful for Greenwich only
class Operators(OwntracksModel):
    topic           = BlobField(null=False)
    tst             = DateTimeField(default=datetime.datetime.now, index=True)
    plmn            = CharField(null=True, max_length=8)
    extended        = CharField(null=True)

class Waypoint(OwntracksModel):
    topic           = BlobField(null=False)
    username        = CharField(null=False)
    device          = CharField(null=False)
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

class Geo(OwntracksModel):
    ghash           = CharField(null=False, max_length=6, unique=True)
    src             = IntegerField(null=True)       # source of reverse geo
    cc              = CharField(null=True, max_length=2)
    addr            = CharField(null=False)



#class Status(OwntracksModel):
#    KEY tid             = CharField(null=False, max_length=2)
#    l_id        location.id
#    g_id        geo.id
#    tstamp          = DateTimeField(default=datetime.datetime.now, index=True)
#    status          = IntegerField(null=True)   # 0, 1, -1
#
#    class Meta:
#        indexes = (
#            # Create a unique index on tst
#            # FIXME:    ----------- (('lat', 'lon', ), True),
#        )

if __name__ == '__main__':
    sql_db.connect()

    if cf.g('features', 'plmn', False) == True:
        try:
            Operators.create_table(fail_silently=True)
        except Exception, e:
            print str(e)

    try:
        Location.create_table(fail_silently=True)
    except Exception, e:
        print str(e)

    try:
        Waypoint.create_table(fail_silently=True)
    except Exception, e:
        print str(e)

    try:
        Geo.create_table(fail_silently=True)
    except Exception, e:
        print str(e)

    if cf.g('features', 'rawdata', False) == True:
        try:
            RAWdata.create_table(fail_silently=True)
        except Exception, e:
            print str(e)

#    try:
#        Status.create_table(fail_silently=True)
#    except Exception, e:
#        print str(e)