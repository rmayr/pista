
__author__    = 'Jan-Piet Mens <jpmens()gmail.com>'
__copyright__ = 'Copyright 2014 Jan-Piet Mens'

try:
    import cPickle as pickle
except ImportError:
    import pickle
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

    def set(self, key, arg):
        return self._request(self.r.set, key, arg)

    def get(self, key=None):
        return self._request(self.r.get, key)

    def hmset(self, key=None, arg=None, expire=None):
        try:
            pipe = self.r.pipeline()
            pipe.hmset(key, arg)
            if expire:
                pipe.expire(key, expire)
            return pipe.execute()
        except:
            pass

        return None

    def hget(self, key=None, field=None):
        return self._request(self.r.hget, key, field)

    def hgetall(self, key=None):
        return self._request(self.r.hgetall, key)

    def lpush(self, key, val):
        return self._request(self.r.lpush, key, val)

    def ltrim(self, key, n, m):
        return self._request(self.r.ltrim, key, n, m)

    def incr(self, key):
        return self._request(self.r.incr, key)

    def hincrby(self, key, field, increment):
        return self._request(self.r.hincrby, key, field, increment)

    def keys(self, pattern):
        return self._request(self.r.keys, pattern)

    def delete(self, key):
        return self._request(self.r.delete, key)

