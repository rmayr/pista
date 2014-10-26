
var users = {};


function getuserlist() {
	$.ajax({
		type: 'GET',
		dataType: "json",
		url: config.userlisturl,
		async: false,
		data: {},
		success: function(data) {
				users = data; 
			},
		error: function(xhr, status, error) {
			alert('getuserlist: ' + status + ", " + error);
			}
	});

	for (var topic in users) {
		var u = users[topic];
		u['count'] = 0;
		// alert("USER=" + JSON.stringify(u));
		// alert(topic + ": " + u.name);
	}
}

function getUser(topic)
{
	return users[topic] = users[topic] || {};
}

function getPopupText(user, lat, lon) {
	var geoloc = getRevGeo(lat,lon);
	var text;
	try {
		text = "<b>" + user.name + "</b><br/>" + lat + ", " + lon + "</br>" + geoloc;
	} catch(err) {
		text = "unknown user<br/>" + lat + ", " + lon + "</br>" + geoloc;
	}
	return text;
}

function getRevGeo(lat, lon) {
	var url = "http://nominatim.openstreetmap.org/reverse?format=json&lat=" + lat + "&lon=" + lon + "&zoom=18&addressdetails=1";
	var output = {}

	$.ajax({
		type: 'GET',
		dataType: "json",
		url: url,
		async: false,
		data: {},
		success: function(data) {
				output = data;
			},
		error: function(xhr, status, error) {
			alert('getRevGeo: ' + status + ", " + error);
			}
	});
	
	var text = "";
	if (output["address"]) {
		if (output["address"]["building"]) {
			text += output["address"]["building"];
		} else if (output["address"]["road"]) {
			text += output["address"]["road"];
			if (output["address"]["house_number"]) {
				text += " " + output["address"]["house_number"];
			}
		} else if (output["address"]["neighbourhood"]) {
			text += output["address"]["neighbourhood"];
			if (output["address"]["house_number"]) {
				text += " " + output["address"]["house_number"];
			}
		}
		
		if (output["address"]["city"]) {
			text += ", " + output["address"]["city"];
		} else if (output["address"]["county"]) {
			text += ", " + output["address"]["county"];
		} else if (output["address"]["country"]) {
			text += ", " + output["address"]["county"];
		}
		return text
	}
	
	return output["display_name"];
}


function friend_add(user, lat, lon)
{
	// Add marker with icon (and text) and return marker object

        var m = L.marker([lat, lon],
                        {
                          // icon: myIcon,
                          icon: L.divIcon({
                                className: 'count-icon',
                                html: user.name, // AK
                                iconSize: [30, 30]
                            }),
                          title: user.lastloc
                        })
                        .addTo(map);
	
	/* Optional: set marker with revgeo */
	/*
	m.bindPopup(getPopupText(user, lat, lon));
	m.on('mouseover', function(evt) {
		evt.target.openPopup();
	});
	*/


	// Bind marker to user
	user.marker = m;

	return user.marker;
}

function friend_move(user, lat, lon)
{
	if (user.marker) {
		user.marker.setLatLng({lat: lat, lng: lon});
		
		/* Use different/alternating class names to switch colour,
		   indicaing movement? */

		map.removeLayer(user.marker);
		user.marker = L.marker([lat, lon], {
			icon: L.divIcon({
				className: 'count-icon',
				html: user.name, // AK
				iconSize: [30, 30]
			}),
                        title: user.lastloc
		}).addTo(map);


		/* Optional: set marker popup, with current rev geo
		user.marker.setPopupContent(getPopupText(user, lat, lon));
		*/
	}

	return user.marker;
}
