% include('tbstop.tpl', page='jobedit', page_title='OwnTracks Jobedit')
%if 'about' in pistapages:

    <!-- Custom styles for this template -->
    <!-- http://vitalets.github.io/x-editable/ -->

    <link href="css/bootstrap-editable.css" rel="stylesheet">
    <script src='js/bootstrap-editable.min.js' type="text/javascript"></script>

    <script type="text/javascript" src="config.js"></script>
    <script type="text/javascript" src="js/mqttws31.js"></script>
    <script src="all/mqtt.js" type="text/javascript"></script>

<script type="text/javascript">

    $.fn.editable.defaults.mode = 'inline';

    var joblist = [];
    var maxjobs = 10;

    for (var i = 0; i < maxjobs; i++) {
    	joblist[i] = "";
    }


    function errorfunc(status, reason) {
        console.log("STATUS: " + status + "; " + reason);
    }
    function handlerfunc(topic, payload) {
	try {
		console.log(topic + " " + payload);

		var i = topic.lastIndexOf("/");
		var pkid = "pk" + topic.substr(i + 1, topic.len); // "pk03"

		var nn = parseInt(topic.substr(i + 1, topic.len));

		joblist[nn] = payload;
		console.log("joblist[" + nn + "] = " + joblist[nn]);

		var pk = $('#' + pkid);
		$(pk).html(joblist[nn]); // Sets visible text and field's default
	
	} catch (err) {
		console.log("handlerfunc: " + err);
		return;
	}
    };

    var tlist = [ config.maptopic ];
    var sub = [];

    // FIXME: tlist must be populated with topic for a particular vehicle
    // FIXME: difficulty: we don't know the topic branch for it!

    tlist = [ 'owntracks/gw/K2/proxy/jobs/+' ];

    for (var n = 0; n < tlist.length; n++) {
		sub.push(tlist[n]);
    }
    mqtt_setup("pista-JOBEDITOR", sub, handlerfunc, errorfunc);
    mqtt_connect();

</script>

    <h2>Activo Job Editor (age)</h2>


<table id='jobtable' class="table table-striped compact nowrap" cellspacing="0" width="100%">
  <colgroup>
    <col span="1" style="width: 10%;">
    <col span="1" style="width: 90%;">
  </colgroup>
<tr><th>Number</th><th>Job</th></tr>

 <tr><td>1</td>
   <td><a href="#" id='pk01' data-pk="01" data-type="text" data-clear="1"></a></td></tr>
 <tr><td>2</td>
   <td><a href="#" id='pk02' data-pk="02" data-type="text" data-clear="1"></a></td></tr>
 <tr><td>3</td>
   <td><a href="#" id='pk03' data-pk="03" data-type="text" data-clear="1"></a></td></tr>
 <tr><td>4</td>
   <td><a href="#" id='pk04' data-pk="04" data-type="text" data-clear="1"></a></td></tr>
 <tr><td>5</td>
   <td><a href="#" id='pk05' data-pk="05" data-type="text" data-clear="1"></a></td></tr>

</table>


<script type="text/javascript">


    $(document).ready(function() {
    	/* Attempt to "wait a bit" so that MQTT has had time to read retained subs ... */
	setTimeout(function(){
		$('#jobtable a').editable({
		    type: 'text',
		    clear: true,
		    name: 'jobdesc',
		    autotext: 'always',
//		    display: function() {
//				/* Get the PK and add joblist[nn] to the column's value */
//				nn = parseInt($(this).data('pk'));
//				
//				$(this).text(joblist[nn]);
//				console.log("Setting text = " + joblist[nn]);
//			   },
		    url:   function(params) {
				// params.name = field name
				// params.value = newly entered value
				// params.pk = 01
				// alert(JSON.stringify(params));
				// alert("Thanks for " + params.pk + " = " + params.value);

				// FIXME: need real topic ...
				var topic = 'owntracks/gw/K2/proxy/jobs/' + params.pk;
				var payload = params.value;
				var qos = 2;
				var retain = true;
				mqtt_publish(topic, payload, qos, retain);
			   },
		    send: 'never',
		    title: 'Enter Job description',
		});
	}, 2000);



    });
</script>


%end
% include('tbsbot.tpl')
