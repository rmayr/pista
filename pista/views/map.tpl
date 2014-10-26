% include('tbstop.tpl', page='map', page_title='OwnTracks LiveMap')



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
    <script src="map/mqttfuncs.js"></script>

<a href="#" id="mqttstatus-details">No connection made yet.</a>

    
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

    <script>
    	$(document).ready(function() {
    		load_map(config.apikey);
    		// getuserlist();
    		MQTTconnect();
    		$('#msg').val('starting');
    	});
    </script>

% include('tbsbot.tpl')
