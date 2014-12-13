// Global variables
var map;
var redIcon;
var latlngs = Array();

/*
 * Draw a geofence (blue circle) on the map for the Geo fence (a.k.a. waypoint).
 * `fence` is an object with the following data:
 * {"lat": 52.3773, "radius": 500, "_type": "fence", "lon": 9.74236, "waypoint": "Hannover HBF"}
 */

function draw_geofence(data)
{
	try{
		lat	= data.lat;
		lon	= data.lon;
		radius	= data.radius;

		L.circle([lat, lon], radius).addTo(map);

	} catch (err) {
		console.log("Cannot draw_geofence " + err);
		return;
	}
}

function load_map(apiKey)
{
	var lat = 51.505;
	var lon = -0.09;

	if (apiKey) {	// Mapbox
		map = L.mapbox.map('map', apiKey).setView([lat, lon], 13);
		var linecolor = 'green';
		var latlngs = Array();
	} else { // OSM
		map = L.map('map').setView([lat, lon], 5);
		mapLink =
		    '<a href="http://openstreetmap.org">OpenStreetMap</a>';
		L.tileLayer(
		    'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
		    attribution: 'Map data &copy; ' + mapLink,
		    maxZoom: 18,
		}).addTo(map);
	}

	map.scrollWheelZoom.disable();
}

// topic is received topic
// d is parsed JSON payload
// date is Date() object
function mapit(topic, d, date)
{
	var user = getUser(topic);
	if (!user || !user.name) {
		// doesn't exist. Create something
		if (d.tid) {
			tid = d.tid;
		} else {
			tid = topic.slice(-2);
		}
		user = {
			name: tid,
			count: 0,
			addr: d.addr,
			info: d.info,
			status: -1,
		};
		users[topic] = user;
	}
		
	var f = {}

	user.status = d.status;
	user.addr   = d.addr;
	user.info   = d.info;

	user.data   = d;

	// console.log(user.name + ": " + user.status);
		
	if (user.marker) {
		f = friend_move(user, d.lat, d.lon);
	} else {
		f = friend_add(user, d.lat, d.lon);
		latlngs.push(f.getLatLng());
		map.fitBounds(L.latLngBounds(latlngs));
	}
}
