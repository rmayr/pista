
var users = {};

function getUser(topic)
{
	return users[topic] = users[topic] || {};
}

function getPopupText(user, lat, lon) {
	var geoloc = user.addr;
	var text;
	try {
		text = "<b>" + user.name + "</b><br/>" + lat + ", " + lon + "</br>" + geoloc;
	} catch(err) {
		text = "unknown user<br/>" + lat + ", " + lon + "</br>" + geoloc;
	}
	return text;
}

function _titlefmt(user) {
	var s = "";

	if (user.info) {
		s = "* " + user.info + "\n";
	}
	if (user.addr) {
		s = s + user.addr;
	}
	return (s);
}

function friend_add(user, lat, lon)
{
	// Add marker with icon (and text) and return marker object
	var className = 'count-icon';
	if (user.status != 1) {
		className = 'count-icon-offline';
	}


        var m = L.marker([lat, lon],
                        {
                          // icon: myIcon,
                          icon: L.divIcon({
                                className: className,
                                html: user.name, // AK
                                iconSize: [30, 30]
                            }),
                          title: _titlefmt(user),
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
	var className = 'count-icon';

	if (user.status != 1) {
		className = 'count-icon-offline';
	}

	if (user.marker) {
		user.marker.setLatLng({lat: lat, lng: lon});
		
		/* Use different/alternating class names to switch colour,
		   indicaing movement? */

		map.removeLayer(user.marker);
		user.marker = L.marker([lat, lon], {
			icon: L.divIcon({
				className: className,
				html: user.name, // AK
				iconSize: [30, 30]
			}),
                        title: _titlefmt(user),
		}).addTo(map);


		/* Optional: set marker popup, with current rev geo */
		user.marker.setPopupContent(getPopupText(user, lat, lon));
	}

	return user.marker;
}
