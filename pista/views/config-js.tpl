/* Generated from jjj.conf for JavaScript */

var config = {

   // These are the hostname or IP address and the port number of the
   // Websockets-enabled MQTT broker. Note: this is the *Websocket* port.


   host:        {{ !host }},
   port:        {{ !port }},
   reconnect_in:        {{ !reconnect_in }},
   usetls:      {{ !usetls }},
   cleansession:      {{ !cleansession }},

   // experiment

   username:    {{ !username if username else "null" }},
   password:    {{ !password if password else "null" }},

   topic: 	{{ !topic }},
   topics: 	{{ !topics }},
   apikey:      {{ !apikey if apikey else "null" }},

   geofences:    {{ !geofences if geofences else "null" }},

   // tables
   topic_visible : {{ !topic_visible }},
   topiclist: {{ !topiclist }},

};
