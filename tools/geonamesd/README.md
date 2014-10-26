# geonamesd

Reverse-Geo lookups can be "expensive" (network-wise) and many online-services
impose hourly or daily limits to the number of queries allowed. In order to
both minimize network traffic and external dependencies, we thought it would
be good to provide an "offline-capable" service. This is what _geonamesd_
pretends to be.

### Geonames database

The [Geonames](http://www.geonames.org) project provides downloadable data
files which cover all countries of the world. 

1. Download the ZIP files of the countries you're interested in and place them
   in `data/zip/`. (Note that these take up quite a bit of space (e.g. `allCountries.zip`) is 262MB at the time of this writing.
2. Run `zip2cdb.py` passing it a list of ZIP files you want loaded into the CDB database.

```bash
$ cd data
$ ./zip2cdb.py zip/DE.zip zip/AT.zip
Reading  DE.txt  ...  19939788
Reading  AT.txt  ...  4998080

$ ls -l *.cdb
-rw-r--r--  1 jpm  staff  10215915 Oct 26 07:22 geonames.cdb
-rw-r--r--  1 jpm  staff  10550345 Oct 26 07:22 latlon.cdb
```

### Compile

1. Run `make' in `kdtree-0.5.6` and in `tinycdb-0.78`
2. Decide on which TCP port you want _geonamesd_ to listen and configure that
   as `HTTP_PORT` in `geonamesd.c` (default: 8081)
3. Run `make`

### Test

Launch `geonamesd` which will listen for an HTTP request on the port you've
configured. Run a GET request with a path to the latitude and longitude you're
interested in:

```
curl http://localhost:8081/47.148148,8.439587
6555913|46.56|DE|Hohentengen am Hochrhein
```

### Requirements

* [mongoose](https://github.com/cesanta/mongoose/) (GPL)
* [kdtree](http://code.google.com/p/kdtree/) (BSD)
* [tinycdb](http://www.corpit.ru/mjt/tinycdb.html) (Public Domain)
