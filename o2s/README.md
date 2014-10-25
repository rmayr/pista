## o2s



#### Reverse-Geo lookups

Every time we receive a location update, we check whether this update is within
reasonable distance from one we already know of, and if so, we use a previously
cached reverse-geo information so as to not impose on online services. This caching
is performed by storing the [geohash](http://en.wikipedia.org/wiki/Geohash) of
the lat,lon pair using
[python-geohash](https://code.google.com/p/python-geohash/), and truncating the
result to six characters.

Consider the following example which illustrates how a six character hash is
equivalent to reducing precision on lat, lon:

```python
import geohash
import sys

lat = 47.488613
lon = 13.187296

print "Original lat,lon: ", lat, lon
full = geohash.encode(float(lat), float(lon))
print "Full geohash: ", full

hashlen = 6

print geohash.encode(47.488613,  13.187296)[:hashlen]
print geohash.encode(47.48861,  13.18729)[:hashlen]
print geohash.encode(47.4886,  13.1872)[:hashlen]
print geohash.encode(47.488,  13.187)[:hashlen]
```

The program outputs:

```
Original lat,lon:  47.488613 13.187296
Full geohash:  u23qhj49nr0d
u23qhj
u23qhj
u23qhj
u23qhh
```

See [geohash.org](http://geohash.org).
