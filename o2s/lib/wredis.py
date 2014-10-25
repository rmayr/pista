
__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'

import redis

class Wredis(object):
    def __init__(self, conf):
        self.enabled = conf.get('enabled', False)
        self.host = conf.get('host')
        self.port = conf.get('port')
        self.db = conf.get('db')
        self.unixsocket = conf.get('unix_socket_path')


        self._reconnect()

    def _reconnect(self):
        if self.unixsocket is None:
            self.r = redis.StrictRedis(self.host, self.port, self.db)
        else:
            self.r = redis.Redis(unix_socket_path=self.unixsocket)

        return self.r

    def _request(self, method, key, *arg):
        if not self.enabled:
            return None
        if self.r is None:
            try:
                self.r = self._reconnect()
            except:
                return None

        try:
            response = method(key, *arg)
            return response
        except:
            return None

    def get(self, key=None):
        return self._request(self.r.get, key)

    def hmset(self, key=None, arg=None, expire=None):
        pipe = self.r.pipeline()
        pipe.hmset(key, arg)
        if expire:
            pipe.expire(key, expire)
        pipe.execute()

    def hget(self, key=None, field=None):
        return self._request(self.r.hget, key, field)

    def hgetall(self, key=None):
        return self._request(self.r.hgetall, key)
