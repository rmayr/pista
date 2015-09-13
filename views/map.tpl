% include('tbstop.tpl', page='map', page_title='OwnTracks LiveMap')
%if 'map' in pistapages:



    <!-- Custom styles for this template -->
    <link href="map/map-style.css" rel="stylesheet">

    <script src='map/mapbox.js' type="text/javascript"></script>
    <link href='map/mapbox.css' rel='stylesheet' />

    <!-- http://code.google.com/p/jqueryrotate/ -->
    <script src="js/jQueryRotateCompressed.js"></script>


    <script src="js/mqttws31.js"></script>
    <script src="config.js"></script>
    <script src="map/userdata.js"></script>
    <script src="map/mapfuncs.js"></script>
    <script src="map/mustache.js"></script>
    <script src="all/mqtt.js" type="text/javascript"></script>
    <script src="js/moment.min.js" type="text/javascript"></script>


    <div id="map" style=""></div>
    <div id='msg'>
	<span id='msg-date'></span>
	<span id='msg-user'></span>
	<span id='msg-cog'><img id='img-cog' src='images/arrow.gif' /></span>
	<span id='msg-revgeo'><a href='#' id='link-revgeo'>xxx</a></span>
	<span id='msg-vel'></span>
	<span id='msg-alt'></span>
	<span id='msg-lat'></span>
	<span id='msg-lon'></span>
    </div>

<script type="text/javascript">
function errorfunc(status, reason) {
        console.log("STATUS: " + status + "; " + reason);
}

function localstamp(tst) {
	/* tst is seconds in UTC. Convert to local time */
	var utcSeconds = tst * 1000;
	var d = moment.utc(utcSeconds).local();

	var output = d.format("DD MMM YYYY HH:mm:ss");

	return output;
}

function handlerfunc(topic, payload) {
	try {
		var d = $.parseJSON(payload);

		if (d._type == 'location') {

			var date = new Date(d.tst * 1000); //convert epoch time to datetime
			var tstamp = localstamp(d.tst);

			d.dstamp = tstamp;	// Override server-data

			$('#msg-date').text(tstamp);
			$('#msg-user').text(d.tid);
			$('#link-revgeo').text(d.addr);
			$('#link-revgeo').prop("href", 'http://maps.google.com/?q=' + d.lat + ',' + d.lon);
			$('#msg-lat').text(d.lat);
			$('#msg-lon').text(d.lon);

			if (d.vel) {
				$('#msg-vel').text(Math.round(d.vel) + "k");
			}
			if (d.alt) {
				$('#msg-alt').text(Math.round(d.alt) + "m");
			}

			if (d.cog) {
				$('#img-cog').show();
				// -90 because original arrow points right (90)
				$('#img-cog').rotate(parseFloat(d.cog) - 90.0);
			} else {
					$('#img-cog').hide();
			}
			mapit(topic, d, date);
		}

		if (d._type == 'fence') {
			draw_geofence(d);
		}
	} catch (err) {
		console.log("JSON parse error " + err);
		return;
	}

};
</script>

<script type="text/javascript">
    	$(document).ready(function() {
		var tlist = [ config.maptopic ];
		var sub = [];

    		load_map(config.apikey);

		for (var n = 0; n < tlist.length; n++) {
			sub.push(tlist[n] + "/" + '+');
			sub.push(tlist[n]);
		}
		mqtt_setup("pista-MAP", sub, handlerfunc, errorfunc);
		mqtt_connect();
    		$('#msg').val('starting');
    	});
</script>

%end
% include('tbsbot.tpl')
