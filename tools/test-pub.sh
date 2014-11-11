#!/bin/sh

set -e

tst=`date +%s`

topic="owntracks/gw/jjolie"

payload='{ "tid": "jj", "_type": "location", "alt": 171, "tst": "'${tst}'", "cog": -1, "batt": "79", "lon": "2.295134", "acc": "10", "vel": 0, "vac": 3, "lat": "48.858334", "t": "t" }'

mosquitto_pub -p 1883 -t "${topic}" -m "${payload}"
