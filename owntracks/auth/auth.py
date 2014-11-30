#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'
__license__   = """Eclipse Public License - v 1.0 (http://www.eclipse.org/legal/epl-v10.html)"""

import sys
import os
import time
import owntracks
import logging
from owntracks.dbschema import User, db
import hashing_passwords as hp

log = logging.getLogger(__name__)

class PistaAuth(object):
    def __init__(self):
        pass

    def check(self, username, password, apns_token=None):

        if username is None or password is None:
            log.error("Username {0} or password are None".format(username))
            return False
    
        try:
            db.connect()
        except Exception, e:
            log.error("%s" % str(e))
            return False

    
        pwhash = None
        try:
            u = User.get(User.username == username)
            pwhash = u.pwhash
        except User.DoesNotExist:
            log.debug("User {0} does not exist".format(username))
            return False
        except Exception, e:
            raise

        match = False

        # Is this a plain-text password in the database?!? OK, we'll do this ...
        if not pwhash.startswith('PBKDF2$'):
            match = pwhash == password
            log.debug('Plain-text password (bah!) match for %s (%s)' % (username, match))
        else:
            match = hp.check_hash(password, pwhash)
            log.debug('Hash match for %s (%s): %s' % (username, pwhash, match))
    
        if match == True and apns_token is not None:
            tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
            try:
                q = User.update(token = apns_token, tstamp = tstamp).where(User.username == username)
                q.execute()
                log.info("Token {0} updated for username={1}".format(apns_token, username))
            except Exception, e:
                log.error("Cannot update User {0} with token {1}: {2}".format(username, apns_token, str(e)))
    
        log.info("Password for username={0} was accepted".format(username))
        return match
