% include('tbstop.tpl', page='tracks', page_title='OwnTracks Tracks')
%if 'tracks' in pistapages:


	<link href="track/track-style.css" rel="stylesheet">
	<link href="css/datepicker.css" rel="stylesheet">
	<link href="css/datepicker3.css" rel="stylesheet">
	<script src="js/bootstrap-datepicker.js" type="text/javascript"></script>


	<script src="track/jstz.min.js" type="text/javascript"></script>
	<script src="config.js" type="text/javascript"></script>
	<script src='map/mapbox.js' type="text/javascript"></script>
	<link href='map/mapbox.css' rel='stylesheet' />
	<script src="map/mapfuncs.js" type="text/javascript"></script>



  <div id='container'>
      <div id='navbar'>

      		<input type='hidden' id='fromdate' value='' />
      		<input type='hidden' id='todate' value='' />

	<div>
	  <p class='description'>
	  Select a <acronym title="Tracker-ID">TID</acronym> and a date or a range of dates. Then
	  click one of the options below to show on map or download data.
	  </p>
	    TID: <select id='usertid'></select>
	    </div>

	<!-- DATE -->
	<div id='datepick'></div>

	<div>
	    Mark every KM:
	    <select id='spacing'>
		<option>2</option>
		<option>5</option>
		<option>10</option>
		<option>20</option>
		<option selected>40</option>
		<option>100</option>
	    </select>
	    </div>


	    <div><a href='#' id='getmap'>Show on map</a></div>
	    <div>
	      Download 
	      {{ have_xls }}
		[<a href='#' fmt='txt' class='download'>TXT</a>]
		[<a href='#' fmt='csv' class='download'>CSV</a>]
		[<a href='#' fmt='gpx' class='download'>GPX</a>]
%if have_xls == True:
		[<a href='#' fmt='xls' class='download'>XLS</a>]
%end
	    </div>

	</div> <!-- end navbar -->

    <div id='content'>
	    <div id="map"></div>
    </div>

    <script type="text/javascript">

    	var map;
	var geojson;
	var line_color = '#ff0000';
	var is_demo = {{ isdemo }}

	load_map(config.apikey);

	var tz = jstz.determine();
	var tzname = tz.name();

	var $select = $('#usertid');
                $.ajax({
                        type: 'GET',
                        url: 'api/userlist',
			// timeout: 30000,
                        async: true,
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


	$('#datepick').datepicker({
	    format: "yyyy-mm-dd",
	    autoclose: true,
	    weekStart: 1, 	// 0=Sunday
	    multidate: 2,
	    multidateSeparator: ',',
	    todayHighlight: true,
	}).on('changeDate', function(e){
		console.log( "UTC=" + JSON.stringify($('#datepick').datepicker('getUTCDates' ))  );
		d = $('#datepick').datepicker('getUTCDates' );

		var d1;
		var d2;

		if (d.length == 1) {
			d1 = new Date(d[0]);
			d2 = d1;
		} else {
			d1 = new Date(d[0]);
			d2 = new Date(d[1]);
		}

		if (d2 < d1) {
			var c = d1;
			d1 = d2;
			d2 = c;
		}

		$('#fromdate').val(isodate(d1));
		$('#todate').val(isodate(d2));
	});

	function onEachFeature(feature, layer) {
		if (feature.properties.geofence) {
			// non-standard GeoJSON
			console.log("onEachFeature " + JSON.stringify(feature.properties.geofence));
			var radius = feature.properties.geofence.radius;
			console.log("RAD=" + radius);

		}

		if (is_demo == false) {

			if (feature.properties.description) {
				layer.bindPopup(feature.properties.description);
			}
		}
	}

	function isodate(d) {
		// http://stackoverflow.com/questions/3066586/
		var yyyy = d.getFullYear().toString();
		var mm = (d.getMonth()+1).toString(); // getMonth() is zero-based
		var dd  = d.getDate().toString();
		var s =  yyyy + "-" +  (mm[1]?mm:"0"+mm[0]) + "-" +  (dd[1]?dd:"0"+dd[0]); // padding

		// console.log(d + ' ---> ' + s);

		return s
	}

	function getGeoJSON() {
		var params = {
			usertid: $('#usertid').children(':selected').attr('id'),
			fromdate: $('#fromdate').val(),
			todate: $('#todate').val(),
			spacing: $('#spacing').val(),
			tzname: tzname,
		};

		// console.log(JSON.stringify(params));

		$.ajax({
			type: 'POST',
                        url: 'api/getGeoJSON',
			async: true,
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

				var fenceMarkerOpts = {
					radius: 2,
					fillColor: 'blue',
					stroke: false,
				};

				if (geojson) {
					map.removeLayer(geojson);
				}
				geojson = L.geoJson(route, {
					style: myStyle,
					pointToLayer: function(feature, latlng) {
						console.log(JSON.stringify(feature.properties));

						/* Smuggling geo-fences in with properties */
						if (feature.properties.geofence) {
							var radius = feature.properties.geofence.radius;
							L.circle([latlng.lat, latlng.lng], radius).addTo(map);
							return L.circleMarker(latlng, fenceMarkerOpts);
						} else {
							return L.circleMarker(latlng, geojsonMarkerOptions);
						}
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
			usertid: $('#usertid').children(':selected').attr('id'),
			fromdate: $('#fromdate').val(),
			todate: $('#todate').val(),
			format: format,
			tzname: tzname,
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


		$('#getmap').on('click', function (e) {
			e.preventDefault();
			getGeoJSON();
		});

		$('.download').on('click', function (e) {
			e.preventDefault();
			// var format = $(e).attr('fmt');
			var format = $(this).attr('fmt');
			console.log(format);
			download(format);
		});

        });
	
    </script>


%end
% include('tbsbot.tpl')
