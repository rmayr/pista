% include('tbstop.tpl', page='console', page_title='OwnTracks Console')
%if 'console' in pistapages:


    <script src="js/mqttws31.js" type="text/javascript"></script>
    <script src="config.js" type="text/javascript"></script>
    <script src="all/mqtt.js" type="text/javascript"></script>
    <link href="console/console-style.css" rel="stylesheet">

<script type="text/javascript">
	function errorfunc(status, reason) {
		console.log("STATUS: " + status + "; " + reason);
	}

	function handlerfunc(topic, payload) {
		$('#ws').prepend('<li>' + payload + '</li>');
	};
</script>

<script type="text/javascript">

	$(document).ready( function () {

	    var tlist = [ config.console_topic ];
	    var sub = [];

	    for (var n = 0; n < tlist.length; n++) {
			sub.push(tlist[n]);
	    }
	    mqtt_setup("pista-CONSOLE", sub, handlerfunc, errorfunc);
	    mqtt_connect();
});
</script>


<h3>MQTT live</h3>
<div>
	<ul id='ws'></ul>
</div>

%end
% include('tbsbot.tpl')
