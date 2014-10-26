% include('tbstop.tpl', page='table', page_title='OwnTracks Table')



    <link href="table/table-style.css" rel="stylesheet">

    <link rel="stylesheet" type="text/css" href="table/dataTables.bootstrap.css">
    <!-- <link rel="stylesheet" type="text/css" href="vendor/jquery.dataTables.css"> -->
    <script type="text/javascript" charset="utf8" src="js/jquery-ui.min.js"></script>
    <script type="text/javascript" charset="utf8" src="table/jquery.dataTables.js"></script>

    <script type="text/javascript" charset="utf8" src="table/dataTables.bootstrap.js"></script>

    <script type="text/javascript" src="config.js"></script>
    <script type="text/javascript" src="js/mqttws31.js"></script>
    <script type="text/javascript" src="table/mqttfuncs.js"></script>

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
        ordering: false,
        autoWidth: false,
        columnDefs: [
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
			title: "Vehicle",
			data: null,
			render: 'vehicle',
                        "targets" : [2],
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
			render: 'tstamp',
                        "targets" : [7],
		},
		{
			className: 'weather',
			name: 'weather',
			title: "Weather",
			data: null,
			render: 'weather',
                        "targets" : [8],
		},
		{
			className: 'degrees',
			name: 'degrees',
			title: "C",
			data: null,
			render: 'degrees',
                        "targets" : [9],
		},
		{
			className: 'batt',
			name: 'batt',
			title: "Batt",
			data: null,
			render: 'batt',
                        "targets" : [10],
                },
		{
			className: 'location',
			name: 'location',
			title: "Location",
			data: null,
			render: 'location',
                        "targets" : [11],
                },
        ],

    });

    $('a.toggle-vis').on('click', function (e) {
        e.preventDefault();
        // Get column API object
        var column = tab.column( $(this).attr('data-column') );
        column.visible( ! column.visible() );
    });

    MQTTconnect();

});
</script>


<div class='toggle-bar'>
Toggle: <a href="#" class="toggle-vis" data-column="0">Topic</a> -
        <a href="#" class="toggle-vis" data-column="6">LatLon</a>
</div>

<div>
        <!-- <table id="livetable" class="display compact hover" cellspacing="0" width="100%"> -->
        <table id="livetable" class="table table-striped compact nowrap" cellspacing="0" width="100%">
        </table>
</div>



% include('tbsbot.tpl')
