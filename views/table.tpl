% include('tbstop.tpl', page='table', page_title='OwnTracks Table')
%if 'table' in pistapages:



    <link href="table/table-style.css" rel="stylesheet">

    <link rel="stylesheet" type="text/css" href="table/dataTables.bootstrap.css">
    <!-- <link rel="stylesheet" type="text/css" href="vendor/jquery.dataTables.css"> -->
    <script type="text/javascript" charset="utf8" src="js/jquery-ui.min.js"></script>
    <script type="text/javascript" charset="utf8" src="table/jquery.dataTables.js"></script>

    <script type="text/javascript" charset="utf8" src="table/dataTables.bootstrap.js"></script>

    <script type="text/javascript" src="config.js"></script>
    <script type="text/javascript" src="js/mqttws31.js"></script>
    <script src="all/mqtt.js" type="text/javascript"></script>
    <script src="js/moment.min.js" type="text/javascript"></script>

<script type="text/javascript">
function errorfunc(status, reason) {
	console.log("STATUS: " + status + "; " + reason);
}

function handlerfunc(topic, payload) {
	try {
		var d = JSON.parse(payload);

		if (d._type != 'location') {
			return;
		}
	
		d.status =  (d.status === undefined) ? null : d.status;
		d.jobname =  (d.jobname === undefined) ? null : d.jobname;
		d.vel = (d.vel) ? Math.round(d.vel) : "";
		d.alt = (d.alt) ? Math.round(d.alt) + "m" : "";

		var latlon = d.lat + "," + d.lon;
		var tstamp = d.dstamp;
		var addr = d.addr;
		var compass = d.compass;
		var tid = d.tid;
		var odo = d.odo ? d.odo : 0;
	
		var mapslink = '<a href="http://maps.google.com/?q=' + latlon + '">' + addr + '</a>';

		var o = {
			topic:          d.topic,
			status:         d.status,
			vehicle:        tid,
			kmh:            d.vel,
			alt:            d.alt,
			cog:            compass,
			latlon:         latlon,
			tstamp:         tstamp,
			addr: 	        addr,
			location:       mapslink,
			tid:            tid,
		        jobname:        d.jobname,
			cc:		d.cc,
			t:		d.t,
			trip:		d.trip,
			odo:		odo,
			imei:		d.imei ? d.imei : "",
			tst:		d.tst,
		};
		upsert(o);
	} catch (err) {
		console.log("JSON parse: " + err);
		return;
	}
};
</script>

<script type="text/javascript">
var tab;

/*
 * Insert data object into table or update existing row. `data' must
 * have 'topic', as that is the key into column 0 of the datatable.
 */

function upsert(data) {

    var found = false;
    var idx;

    tab.rows().indexes().each( function(idx) {
        var d = tab.row(idx).data();
        if (d && (d.topic == data.topic)) {
                found = true;
                /* idx is index of updated row (0--n) */
                idx = tab.row(idx).data(data);
                /* Highlight */
                var row = tab.rows(idx, {order:'index'}).nodes().to$();
                $(row).animate({ 'backgroundColor': '#FF9900' }, 650, function(){
                        $(row).animate({'backgroundColor': 'white'}, 650);
                });
            }
    });

    if (!found) {
            idx = tab.row.add(data);
    }
    tab.draw();
}

$(document).ready( function () {
    var counter = 0;
    tab = $('#livetable').DataTable({
        paging: false,
        searching: false,
        ordering: true,
        autoWidth: false,
	order: [[ 2, "asc" ]],
        columnDefs: [
		{ orderable : true, targets: [2] },

                {
                        className: 'topic',
                        name: 'topic',
                        title: "Topic",
                        visible: config.topic_visible,
                        data: null,
                        render: 'topic',
                        "targets" : [0],
                },
                {
        		className: 'status',
			name: 'status',
			title: "",
			visible: true,
			data: null,
                        "targets" : [1],
			render : function(data, type, row) {
				var icons = ['yellow', 'red', 'green' ];
				if (data.status === null || data.status === undefined) {
					return "";
				}
				data.status += 1;

				var icon = icons[data.status];
				if (icon === undefined) {
					return data.status;
				}

				return '<img src="images/' + icon + 'dot.gif" />';
			}
                },
		{
			className: 'vehicle',
			name: 'vehicle',
			title: "TID/IMEI",
			data: null,
			render: 'vehicle',
                        "targets" : [2],
			render : function(data, type, row) {

				return '<acronym title="' + data.imei + '">' + data.tid + '</acronym>';
			}
		},
		{
			className: 'kmh',
			name: 'kmh',
			title: "kmh",
			data: null,
			render: 'kmh',
                        "targets" : [3],
		},
		{
			className: 'alt',
			name: 'alt',
			title: "Alt",
			data: null,
			render: 'alt',
                        "targets" : [4],
		},
		{
			className: 'cog',
			name: 'cog',
			title: "CoG",
			data: null,
			render: 'cog',
                        "targets" : [5],
		},
		{
			className: 'latlon',
			name: 'latlon',
			title: "Lat/Lon",
			data: null,
			render: 'latlon',
                        visible: false,
                        "targets" : [6],
		},
		{
			className: 'tstamp',
			name: 'tstamp',
			title: "Time",
			data: null,
                        "targets" : [7],
			render : function(data, type, row) {

				/* tst is seconds in UTC. Convert to local time
				 * using moment(). Check if day differs from 'today'
				 * and if so, mark the day specifically. This returns
				 * a string. Either:
				 *	HH:MM:SS
				 * or
				 * 	dd<HH:MM:SS
				 */
				var utcSeconds = data.tst * 1000;
				var d = moment.utc(utcSeconds).local();

				var daystring = d.format("DD");
				var timestring = d.format("HH:mm:ss");
				var fulldate = d.format("DD MMM YYYY HH:mm:ss");

				var output = "";
				var now = moment();
				if ((now.get('year') == d.get('year')) &&
					(now.get('month') == d.get('month')) &&
					(now.get('date') != d.get('date'))) {
					output = daystring + "&lsaquo;";
				} else {
					if ( (now.get('month') != d.get('month')) ||
					     (now.get('date') != d.get('date'))
					   )
					{
						output = daystring + "&lsaquo;";
					}
				}
				output = output + timestring;

				return '<acronym title="' + fulldate + '">' + output + '</acronym>';
			}
		},
		{
			className: 'cc',
			name: 'cc',
			title: "CC",
			data: null,
			render: 'cc',
                        "targets" : [8],
                },
		{
			className: 't',
			name: 't',
			title: "T",
			data: null,
                        "targets" : [9],
			render : function(data, type, row) {
				var t = data.t;
				var desc = 'Unknown';
				var descriptions = {
				  "f": "First pub after reboot",
				  "c": "Started by alarm clock",
				  "a": "Alarm (accelerometer)",
				  "k": "Transition to park",
				  "L": "Last recorded before graceful shutdown",
				  "l": "GPS signal lost",
				  "u": "Manually requested",
				  "t": "Device is moving",
				  "T": "Stationary; maxInterval has elapsed",
				  "v": "Transition from park to move",
				};

				try {
					desc = descriptions[t];
				} catch(err) {
					desc = '???';
				}

				return '<acronym title="' + desc + '">' + t + '</acronym>';
			}
                },
		{
			className: 'location',
			name: 'location',
			title: "Location",
			data: null,
			render: 'location',
                        "targets" : [10],
                },
                {
                        className: 'jobname',
                        name: 'jobname',
                        title: "Job",
                        data: null,
                        render: 'jobname',
			visible: config.activo, // True if Activo true
                        "targets" : [11],
                },
		{
			className: 'trip',
			name: 'trip',
			title: "Trip/Odo",
			data: null,
                        "targets" : [12],
			render : function(data, type, row) {
				trip = data.trip;
				odo = data.odo;
				trip = Math.round(trip / 1000);

				realodo = odo + trip;

				return '<acronym title="' + realodo + '">' + trip + '</acronym>';
			}
                },
        ],

    });

    $('a.toggle-vis').on('click', function (e) {
        e.preventDefault();
        // Get column API object
        var column = tab.column( $(this).attr('data-column') );
        column.visible( ! column.visible() );
    });


    var tlist = [ config.maptopic ];
    var sub = [];

    for (var n = 0; n < tlist.length; n++) {
		sub.push(tlist[n]);
    }
    mqtt_setup("pista-TABLE", sub, handlerfunc, errorfunc);
    mqtt_connect();

});
</script>


<div class='toggle-bar'>
Toggle: <a href="#" class="toggle-vis" data-column="0">Topic</a> -
        <a href="#" class="toggle-vis" data-column="6">LatLon</a>
%if activo == True:
        - <a href="#" class="toggle-vis" data-column="11">Job</a>
%end
</div>

<div>
        <!-- <table id="livetable" class="display compact hover" cellspacing="0" width="100%"> -->
        <table id="livetable" class="table table-striped compact nowrap" cellspacing="0" width="100%">
        </table>
</div>

%end
% include('tbsbot.tpl')
