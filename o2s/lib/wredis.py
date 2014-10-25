
import redis

class Wredis(object):
    def __init__(self, enabled=0, host='localhost', port=6379, db=0, unixsocket=None):
        self.enabled = enabled
        self.host = host
        self.port = port
        self.db = db
        self.unixsocket = unixsocket

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

    def hmset(self, key=None, arg=None):
        return self._request(self.r.hmset, key, arg)

    def hget(self, key=None, field=None):
        return self._request(self.r.hget, key, field)

    def hgetall(self, key=None):
        return self._request(self.r.hgetall, key)
