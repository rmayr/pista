/* Generated from {{ configfile }} for JavaScript */

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

   apikey:      {{ !apikey if apikey else "null" }},

   // tables
   topic_visible : {{ !topic_visible }},

   // Console
   console_topic: {{ !console_topic }},

   // Map and Table
   maptopic: {{ !maptopic }},

   // Job
   jobtopic: {{ !jobtopic }},

   // Activo enabled?
   activo: {{ !activo }},

};
