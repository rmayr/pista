% include('tbstop.tpl', page='jobs', page_title='OwnTracks Jobs')
%if 'jobs' in pistapages:



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

		var duration = null;
		if (d.jobduration != null && d.jobduration != undefined) {
			var hours = Math.floor(d.jobduration / 3600);
			var minutes = Math.floor((d.jobduration % 3600) / 60);
			var seconds = Math.floor((d.jobduration % 3600) % 60); 
			if (hours === 0 && minutes === 0) {
				duration = seconds + "s";
			} else if (hours === 0) {
				duration = minutes + "m " + seconds + "s";
			} else {
				duration = hours + "h " + minutes + "m";
			}
		}
	
		var o = {
			topic:          d.topic,
			tid:		d.tid,
			job:		d.job,
			jobname:	d.jobname,
			jobstart:	d.jobstart,
			jobend:		d.jobend,
			duration:	duration,
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
    tab = $('#livejobs').DataTable({
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
				var icon = 'red';
				if (data.jobend === null || data.jobend === undefined) {
					icon = 'green';
				}
				return '<img src="images/' + icon + 'dot.gif" />';
			}
                },
		{
			className: 'vehicle',
			name: 'vehicle',
			title: "TID",
			data: null,
			render: 'tid',
                        "targets" : [2],
		},
		{
			className: 'job',
			name: 'job',
			title: "Job ID",
			data: null,
			render: 'job',
                        visible: false,
                        "targets" : [3],
		},
		{
			className: 'jobname',
			name: 'jobname',
			title: "Job",
			data: null,
			render: 'jobname',
                        "targets" : [4],
		},
		{
			className: 'jobstart',
			name: 'jobstart',
			title: "Start",
			data: null,
                        "targets" : [5],
			render : function(data, type, row) {

				/* tst is seconds in UTC. Convert to local time
				 * using moment(). Check if day differs from 'today'
				 * and if so, mark the day specifically. This returns
				 * a string. Either:
				 *	HH:MM:SS
				 * or
				 * 	dd<HH:MM:SS
				 */
                                if (data.jobstart === null || data.jobstart === undefined) {
                                        return null;
                                }

				var utcSeconds = data.jobstart * 1000;
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
                        className: 'jobend',
                        name: 'jobend',
                        title: "End",
                        data: null,
                        "targets" : [6],
                        render : function(data, type, row) {

                                /* tst is seconds in UTC. Convert to local time
                                 * using moment(). Check if day differs from 'today'
                                 * and if so, mark the day specifically. This returns
                                 * a string. Either:
                                 *      HH:MM:SS
                                 * or
                                 *      dd<HH:MM:SS
                                 */
				if (data.jobend === null || data.jobend === undefined) {
					return null;
				}

                                var utcSeconds = data.jobend * 1000;
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
                        className: 'duration',
                        name: 'duration',
                        title: "Duration",
                        data: null,
                        render: 'duration',
                        "targets" : [7],
                },
        ],

    });

    $('a.toggle-vis').on('click', function (e) {
        e.preventDefault();
        // Get column API object
        var column = tab.column( $(this).attr('data-column') );
        column.visible( ! column.visible() );
    });


    var tlist = [ config.jobtopic ];
    var sub = [];

    for (var n = 0; n < tlist.length; n++) {
		sub.push(tlist[n]);
    }
    mqtt_setup("pista-JOBS", sub, handlerfunc, errorfunc);
    mqtt_connect();

});
</script>


<div class='toggle-bar'>
Toggle: <a href="#" class="toggle-vis" data-column="0">Topic</a> - 
        <a href="#" class="toggle-vis" data-column="3">Job ID</a>
</div>

<div>
        <!-- <table id="livejobs" class="display compact hover" cellspacing="0" width="100%"> -->
        <table id="livejobs" class="table table-striped compact nowrap" cellspacing="0" width="100%">
        </table>
</div>

%end
% include('tbsbot.tpl')
