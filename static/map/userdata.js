
var users = {};

function getUser(topic)
{
	return users[topic] = users[topic] || {};
}

function getPopupText(user, lat, lon) {
	var text = "";

	var template = "\
		<table id='infopopup'>\
			<tr><td>TID</td><td>{{tid}}</td></tr>\
			<tr><td>IMEI</td><td>{{imei}}</td></tr>\
			<tr><td>Info</td><td><b>{{info}}</b></td></tr>\
			<tr><td>Addr</td><td>{{addr}}</td>\
			<tr><td>Location</td><td>{{lat}}, {{lon}}</td></tr>\
			<tr><td>Speed</td><td>{{vel}}</td></tr>\
			<tr><td>Altitude</td><td>{{alt}}</td></tr>\
			<tr><td>CoG</td><td>{{compass}}</td></tr>\
			<tr><td>Updated</td><td>{{dstamp}}</td></tr>\
			<tr><td>Job</td><td>{{jobname}}</td></tr>\
		</table>";

	try {
		text = Mustache.render(template, user.data);
	} catch(err) {
		text = "Cannot render Mustache";
	}
	return text;
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
                          // title: _titlefmt(user),
                        })
                        .addTo(map);
	
	/* Optional: set marker with revgeo */
	m.bindPopup(getPopupText(user, lat, lon));
	m.on('mouseover', function(evt) {
		evt.target.openPopup();
	});


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
                        // title: _titlefmt(user),
		}).addTo(map);


		/* Optional: set marker popup, with current rev geo */
		user.marker.bindPopup(getPopupText(user, lat, lon));
		// user.marker.setPopupContent(getPopupText(user, lat, lon));
		user.marker.on('mouseover', function(evt) {
			evt.target.openPopup();
		});
	}

	return user.marker;
}
