% include('tbstop.tpl', page='hw', page_title='OwnTracks Hardware')


    <script src="js/jquery.flot.min.js" type="text/javascript"></script>
    <script src="js/jquery.flot.categories.min.js" type="text/javascript"></script>
    <script src="js/jquery.sparkline.min.js" type="text/javascript"></script>


	<script type="text/javascript">

	$(function() {

		$('.inlinebar').sparkline('html', {
			type: 'bar', barColor: 'blue', disableInteraction: true,  });

		var data = [];

                options = {
                        series: {
                                bars: {
                                        show: true,
                                        barWidth: 0.6,
                                        align: "center"
                                }
                        },
                        xaxis: {
                                mode: "categories",
                                tickLength: 0
                        }
                };

		var alreadyFetched = {};

		function onDataReceived(series) {

				// Extract the first coordinate pair; jQuery has parsed it, so
				// the data is now just an ordinary JavaScript object

				var firstcoordinate = "(" + series.data[0][0] + ", " + series.data[0][1] + ")";
				// button.siblings("span").text("Fetched " + series.label + ", first point: " + firstcoordinate);

				// Push the new data onto our existing data array

				if (!alreadyFetched[series.label]) {
					alreadyFetched[series.label] = true;
					data.push(series);
				}

				$.plot("#placeholder", data, options);
		}

			$.ajax({
				url: "api/flotbatt/ext",
				type: "GET",
				dataType: "json",
				success: onDataReceived
			});

	});

	</script>

	<div id="placeholder" style="height:200px;"></div>


<h3>Devices</h3>
<table class='table table-striped table-condensed'>
<thead>
  <tr>
  	<th>Topic</th>
	<th>TID</th>
	<th>IMEI</th>
	<th>Version</th>
	<th>Startup</th>
	<th>Batt</th>
	<th>Ext</th>
    </tr>
  </thead>
<tbody>

% import json
% sdict = json.load(open('p/status.json')) #FIXME: filename? configurable?
% for dev in sdict:
%    d = sdict[dev]
%    vbatt = ", ".join(map(str, d.get('batt', [0, 0, 0, 0])))
%    vext  = ", ".join(map(str, d.get('ext', [0, 0, 0, 0])))
     <tr>
        <td>{{dev}}</td>
	<td>{{ d.get('tid', dev[-2:]) }}</td>
	<td>{{ d.get('imei', '') }}</td>
     	<td>{{ d.get('version', '') }}</td>
     	<td>{{ d.get('tstamp', '') }}</td>
	<td><span class='inlinebar'>{{ vbatt }}</span></td>
	<td><span class='inlinebar'>{{ vext }}</span></td>
       </tr>
% end

</tbody>
</table>


% include('tbsbot.tpl')
