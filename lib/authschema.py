#!/usr/bin/env python

from peewee import *
from cf import conf
import datetime
import os
import sys

cf = conf(os.getenv('O2SCONFIG', 'o2s.conf'))

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


class ConferModel(Model):

    class Meta:
        database = sql_db


class User(ConferModel):
    username        = CharField(null=False, unique=True)
    pwhash          = CharField(null=False)
    superuser       = IntegerField(null=False)
    org             = IntegerField(null=True)
    token           = CharField(null=True)
    note            = CharField(null=True)
    tstamp          = DateTimeField(default=datetime.datetime.now)


class Acl(ConferModel):
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

class Params(ConferModel):
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

#class Tidlist(ConferModel):
#    user            = ForeignKeyField(User)
#    tid             = CharField(null=False)
#
#    class Meta:
#        indexes = (
#            # Create unique on user, tid
#            (('user', 'tid'), True),
#        )


if __name__ == '__main__':
    sql_db.connect()

    if cf.g('features', 'ctrldauth', False) == True:
        try:
            User.create_table(fail_silently=True)
        except Exception, e:
            print str(e)

        try:
            Acl.create_table(fail_silently=True)
        except Exception, e:
            print str(e)

        try:
            Params.create_table(fail_silently=True)
        except Exception, e:
            print str(e)

#        try:
#            Tidlist.create_table(fail_silently=True)
#        except Exception, e:
#            print str(e)
