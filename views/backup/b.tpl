% include('tbstop.tpl', page_title='Page AAAA')





  <div id='container'>
      <div id='navbar'>

	<ul>
	    <li>User/Device: <select id='userdev'></select></li>
	    <li>From: <input type='text' id='fromdate' value='2014-08-19' /></li>
	    <li>To: <input type='text' id='todate' value='2014-08-20' /></li>


	    <li>Point every KM: 
	    <select id='spacing'>
		<option selected>2</option>
		<option>5</option>
		<option>10</option>
		<option>20</option>
		<option>40</option>
	    </select></li>


	    <div id='datep'></div>

	    <li>Color: 	<div id="colorPicker1">
                    <a class="color"><div class="colorInner"></div></a>
                    <div class="track"></div>
                    <ul class="dropdown"><li></li></ul>
                    <input type="hidden" class="colorInput"/>
		</div></li>


	    <li><a href='#' id='getmap'>Show on map</a></li>
	    <li>Download
	    	<ul>
		    <li><a href='#' id='dn_txt'>TXT</a></li>
		    <li><a href='#' id='dn_csv'>CSV</a></li>
		    <li>GPX</li>
		    <li>GeoJSON</li>
		    </ul>
		</li>

	</ul>

	    <!-- <a href='#' id='nextdate'>Next</a> -->
	</div> <!-- end navbar -->

    <div id='content'>
	    <div id="map"></div>
    </div>

    <script type="text/javascript">

    	var map;
	var geojson;
	var line_color = '#ff0000';

    	var lat = 50.109544;
	var lon = 8.694585;

        map = L.map('map').setView([lat, lon], 5);
        mapLink = 
            '<a href="http://openstreetmap.org">OpenStreetMap</a>';
	L.tileLayer(
            'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: 'Map data &copy; ' + mapLink,
            maxZoom: 18,
	}).addTo(map);


	var $select = $('#userdev');
                $.ajax({
                        type: 'GET',
                        url: 'api/userlist',
                        async: false,
			success: function(data) {

				// clear current content of select
				$select.html('');

				// iterate and append
				$.each(data.userlist, function(key, val) {
					$select.append('<option id="' + val.id + '">' +
						val.name + '</option>');
				})
			    },
			error: function() {
				$select.html("none available");
				}
		});

	$('#datep').DatePicker({
		flat: true,
		date: ['2014-08-19', '2014-08-20'],
		current: '2014-08-26',
		calendars: 2,
		mode: 'range',
		starts: 1,
		onChange: function(formatted, dates) {
			// console.log(formatted);
			// console.log(dates);

			$('#fromdate').val(formatted[0]);
			$('#todate').val(formatted[1]);
		},
	});

	function onEachFeature(feature, layer) {
		if (feature.properties) {
			layer.bindPopup(feature.properties.description);
		}
	}

	function getGeoJSON() {
		var params = {
			userdev: $('#userdev').children(':selected').attr('id'),
			fromdate: $('#fromdate').val(),
			todate: $('#todate').val(),
			spacing: $('#spacing').val(),
		};

		// console.log(JSON.stringify(params));

		$.ajax({
			type: 'POST',
                        url: 'api/getGeoJSON',
			async: false,
			data: JSON.stringify(params),
			dataType: 'json',
			success: function(data) {
				// console.log(JSON.stringify(data));

				route = data;

                /* FIXME: need to get style from geoJSON maybe? This overrides
                   default style for points, which makes it hard to see them */

				var myStyle = {
				    "color": line_color,
				    "weight": 5,
				    "opacity": 0.65
			        };

				var geojsonMarkerOptions = {
				    radius: 6,
				    fillColor: "#ffffff",
				    color: "#000",
				    weight: 1,
				    opacity: 1,
				    fillOpacity: 0.8
				};

				if (geojson) {
					map.removeLayer(geojson);
				}
				geojson = L.geoJson(route, {
					style: myStyle,
					pointToLayer: function(feature, latlng) {
						return L.circleMarker(latlng, geojsonMarkerOptions);
					},
					onEachFeature: onEachFeature
				}).addTo(map);

				try {
					map.fitBounds(geojson.getBounds());
				} catch (err) {
					// console.log(err);
				}


			},
			error: function(xhr, status, error) {
				alert('get: ' + status + ", " + error);
			}
		   });
	}

	function download(format) {
		var params = {
			userdev: $('#userdev').children(':selected').attr('id'),
			fromdate: $('#fromdate').val(),
			todate: $('#todate').val(),
			format: format,
		};

		$.fileDownload('api/download', {
			data: params,
			successCallback: function(url) {
				console.log("OK URL ", + url);
			},
			failCallback: function(html, url) {
				console.log("ERROR " + url + " " + html);
			}
		});
	}

	$(document).ready(function() {


		// FIXME: $("#colorPicker1").setColor(line_color);
		$("#colorPicker1").tinycolorpicker();
		$("#colorPicker1").bind("change", function() {
			line_color = $(".colorInput").val();
		});

		$('#getmap').on('click', function (e) {
			e.preventDefault();
			getGeoJSON();
		});

		$('#dn_txt').on('click', function (e) {
			e.preventDefault();
			download('txt');
		});

		$('#dn_csv').on('click', function (e) {
			e.preventDefault();
			download('csv');
		});


		$('#nextdate').on('click', function (e) {
			e.preventDefault();

			var d_from;
			var d_to;


			var d = $('#datep').DatePickerGetDate(false);
			// console.log(d);
			d_from = new Date(d[0]);
			d_to   = new Date(d[1]);

			d_from = d_from.setDate(d_from.getDate() + 1);
			d_to   = d_to.setDate(d_to.getDate() + 1);

			$('#datep').DatePickerSetDate(d_to, true);

			$('#todate').val( $('#datep').DatePickerGetDate(true)[1] );

		});


        });
	
    </script>


% include('tbsbot.tpl')
