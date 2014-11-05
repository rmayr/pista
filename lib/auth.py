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
        self.logging = logging.getLogger(__name__)
        pass

    def check(self, username, password, apns_token=None):

        if username is None or password is None:
            self.logging.error("Username {0} or password are None".format(username))
            return False
    
        try:
            sql_db.connect()
        except Exception, e:
            self.logging.error("%s" % str(e))
            return False

        # FIXME: handle non-pbdkf2 passwords (i.e. plain)
    
        pwhash = None
        try:
            u = User.get(User.username == username)
            pwhash = u.pwhash
        except User.DoesNotExist:
            self.logging.debug("User {0} does not exist".format(username))
            return False
        except Exception, e:
            raise

        match = hp.check_hash(password, pwhash)
        self.logging.debug('Hash match for %s (%s): %s' % (username, pwhash, match))
    
        if match == True and apns_token is not None:
            tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
            try:
                q = User.update(token = apns_token, tstamp = tstamp).where(User.username == username)
                q.execute()
                self.logging.info("Token {0} updated for username={1}".format(apns_token, username))
            except Exception, e:
                self.logging.error("Cannot update User {0} with token {1}: {2}".format(username, apns_token, str(e)))
    
        self.logging.info("Password for username={0} was accepted".format(username))
        return match
