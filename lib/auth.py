#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'

import sys
import os
import time
import logging
from dbschema import User, sql_db
import hashing_passwords as hp

class PistaAuth(object):
    def __init__(self):
        pass

    def check(self, username, password, apns_token=None):

        if username is None or password is None:
            logging.error("Username {0} or password are None".format(username))
            return False
    
        try:
            sql_db.connect()
        except Exception, e:
            logging.error("%s" % str(e))
            return False
    
        pwhash = None
        try:
            u = User.get(User.username == username)
            pwhash = u.pwhash
        except User.DoesNotExist:
            logging.debug("User {0} does not exist".format(username))
            return False
        except Exception, e:
            raise
    
    
    
        match = hp.check_hash(password, pwhash)
        logging.debug('Hash match for %s (%s): %s' % (username, pwhash, match))
    
        if match == True and apns_token is not None:
            tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
            try:
                q = User.update(token = apns_token, tstamp = tstamp).where(User.username == username)
                q.execute()
            except Exception, e:
                logging.error("Cannot update User {0} with token {1}: {2}".format(username, apns_token, str(e)))
    
        return match
