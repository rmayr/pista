var reconnectTimeout = 3000;
var mqtt;

function MQTTconnect()
{
	mqtt = new Messaging.Client(config.host, config.port,
				"leaf" + parseInt(Math.random() * 100, 10));

	mqtt.onConnectionLost = function (responseObject) {
		setTimeout(MQTTconnect, reconnectTimeout);
		$('#mqttstatus').html("Connection lost");
		$('#mqttstatus-details').html(responseObject.errorMessage);
		console.log(responseObject.errorMessage);
	};

	mqtt.onMessageArrived = function (message) {
		topic = message.destinationName;

		try {
			payload = message.payloadString;
			var d = $.parseJSON(payload);
			// console.log(payload);

			if (d._type != 'location') {
				return;
			}
			var date = new Date(d.tst * 1000); //convert epoch time to datetime
			var tstamp = date.toLocaleString();

			var user = getUser(topic);
			if (user && user.name) {
				/* FIXME: remove; do NOT perform GEO update in map
				if ((user.count % config.geoupdate) == 0) {
					user['lastloc'] = getRevGeo(d.lat, d.lon);
					console.log("User: " + user.name + " RevGeo=" + user.lastloc);
				}
				*/
				user.count++;
				console.log("User: " + user.name + " " + user.count);

			}

			$('#msg-date').text(tstamp);
			$('#msg-user').text(user.name);
			$('#msg-lat').text(d.lat);
			$('#msg-lon').text(d.lon);

			$('#link-revgeo').text(user.lastloc);
			$('#link-revgeo').prop("href", 
				 'http://maps.google.com/?q=' + d.lat + ',' + d.lon);

			if (d.vel) {
				$('#msg-vel').text(Math.round(d.vel) + "k");
			}
			if (d.alt) {
				$('#msg-alt').text(Math.round(d.alt) + "m");
			}

			/* Course over Ground */

			if (d.cog) {
				$('#img-cog').show();
				// -90 because original arrow points right (90)
				$('#img-cog').rotate(parseFloat(d.cog) - 90.0);
			} else {
				$('#img-cog').hide();
			}

			// console.log(topic + " " + d.lat + ", " + d.lon);
		} catch (err) {
			console.log("JSON parse error " + err);
			return;
		}

		mapit(topic, d, date);

	};

	var options = {
		timeout: 60,
		useSSL: config.usetls,
		onSuccess: function () {
			$('#mqttstatus').html("Connected");
			$('#mqttstatus-details').html("Host: " + config.host + ", Port:" +  config.port);
			mqtt.subscribe(config.topic, {qos: 0});
		},
		onFailure: function (message) {
			$('#mqttstatus').html("Connection failed");
			$('#mqttstatus-details').html(message.errorMessage);
			setTimeout(MQTTconnect, reconnectTimeout);
		}
	};

        if (config.username != null) {
            options.userName = config.username;
            options.password = config.password;
        }

	/* Connect to MQTT broker */
	mqtt.connect(options);
}

