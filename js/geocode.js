/**
 *  Functions for Geo-Coding.
 */

var g_map = null;
var g_geocoder = null;


function locatePatient() {
	$('#g_map').show();
	
	var adr = $('#patient_location').text();
	if (adr) {
		geocodeAddress(adr);
	}
}

function hideMap() {
	$('#g_map').hide();
}

/**
 *  Locate the address via Google and display in our map.
 */
function geocodeAddress(address) {
	if (!address) {
		console.error("No address given, cannot geo-code");
		return null;
	}
	
	// create coder and map if needed
	if (!g_geocoder) {
		g_geocoder = new google.maps.Geocoder();
	}
	if (!g_map) {
		var mapOptions = {
			zoom: 7,
			center: new google.maps.LatLng(42.358, -71.06),
			mapTypeId: google.maps.MapTypeId.ROADMAP
		}
		g_map = new google.maps.Map($("#g_map").get(0), mapOptions);
	}
	
	// code!
	g_geocoder.geocode({
		'address': address
	},
	function(results, status) {
		console.log("RESULTS", results);
		if (google.maps.GeocoderStatus.OK == status) {
			g_map.setCenter(results[0].geometry.location);
			var marker = new google.maps.Marker({
				map: g_map,
				position: results[0].geometry.location
			});
		}
		else if (google.maps.GeocoderStatus.ZERO_RESULTS) {
			alert("The address \"" + address + "\" could not be located.");
		}
		else {
			console.error("Geocode failed: " + status);
		}
	});
 }
