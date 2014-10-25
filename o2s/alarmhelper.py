
def alarmplugin(topic, item, mosq):
    """
    topic is the MQTT topic the alarm was received on
    The item{} dict contains a location entry as received by o2s.
    In any case it'll contain 'lat' and 'lon'.
    mosq is an open connection to MQTT
    """

    lat = item['lat']
    lon = item['lon']
    
    # use lat, lon and do something

    s = "***** ALARM FOR tid=%s (%s): lat=%s, lon=%s" % (item['tid'], topic, lat, lon)
    print s

    ## mosq.publish("owntracks/gw/**ALARM", bytearray(s.encode('utf-8')), qos=0, retain=False)
