/* JP Mens, September 2014 */
var reconnectTimeout = (config.reconnect_in) ? config.reconnect_in : 3000;
var mqtt;

/*
 * topiclist is array of topics [ 'one/+', 'two/#', ...]
 * handlerfunc is invoked for each incoming MQTT message
 * and it is passed a topic and the payload string
 * errorfunc() is invoked upon error with a status (set here)
 * and the error string from the library.
 */

function mqtt_setup(clientid, topiclist, handlerfunc, errorfunc) {
        if (typeof mqtt_setup.topiclist == 'undefined') {
                // initialize
                mqtt_setup.topiclist = [];

		mqtt_setup.clientid = clientid;
		mqtt_setup.handlerfunc = handlerfunc;
		mqtt_setup.errorfunc   = errorfunc;

                for (n in topiclist) {
                        mqtt_setup.topiclist.push(topiclist[n]);
                }

        }
}

function mqtt_connect()
{
	// Renamed in https://bugs.eclipse.org/bugs/show_bug.cgi?id=448136

	var clientid = mqtt_setup.clientid + parseInt(Math.random() * 100, 10);

	console.log("Will create MQTT connection to " + config.host + ":" + config.port +
			" clientid:" + clientid);

	// mqtt = new Paho.MQTT.Client(config.host, config.port, clientid);
	mqtt = new Messaging.Client(config.host, config.port, clientid);

	mqtt.onConnectionLost = function (responseObject) {
		setTimeout(mqtt_connect, reconnectTimeout);
		console.log(responseObject.errorMessage);
		mqtt_setup.errorfunc("Connection lost", responseObject.errorMessage);
	};

	mqtt.onMessageArrived = function (message) {
		topic = message.destinationName;
		payload = message.payloadString;

		try {
			mqtt_setup.handlerfunc(topic, payload);
		} catch (err) {
			console.log("mqtt_setup.handlerfunc: " + err);
		}
	};

	var options = {
		timeout: 60,
		useSSL: config.usetls,
		onSuccess: function () {
			console.log("Host: " + config.host + ", Port:" +  config.port);
			mqtt_setup.errorfunc("Connected", config.host + ":" +  config.port);
			for (n in mqtt_setup.topiclist) {
				topic = mqtt_setup.topiclist[n];
				console.log("subscribe to " + topic);
				mqtt.subscribe(topic, {qos: 0});
			}
		},
		onFailure: function (message) {
			console.log(message.errorMessage);
			mqtt_setup.errorfunc("Connection failed", message.errorMessage);
			setTimeout(mqtt_connect, reconnectTimeout);
		}
	};
        if (config.username != null) {
            options.userName = config.username;
            options.password = config.password;
        }

	/* Connect to MQTT broker */
	mqtt.connect(options);
}

function mqtt_publish(topic, payload, qos, retain)
{
	var message = new Messaging.Message(payload);

	if (typeof(qos) === 'undefined') qos = 0;
	if (typeof(retain) === 'undefined') retain = 0;

	message.destinationName = topic;
	message.qos		= qos;
	message.retained	= retain;

	console.log("MQTT PUB " + topic + ", " + payload)
	try {
		mqtt.send(message);
	} catch (err) {
		console.log("mqtt.send: " + err);
	}
}
