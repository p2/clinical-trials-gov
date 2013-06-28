/**
 *  Functions for Geo-Coding.
 */

var g_map = null;
var g_geocoder = null;

var g_pins = [];
var g_highlighted_pin = null;


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
			zoom: 4,
			// center: new google.maps.LatLng(42.358, -71.06),
			center: new google.maps.LatLng(38.5, -96.5),
			mapTypeId: google.maps.MapTypeId.ROADMAP
		}
		g_map = new google.maps.Map($("#g_map").get(0), mapOptions);
	}
	
	// code!
	g_geocoder.geocode({
		'address': address
	},
	function(results, status) {
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

/**
 *  Adds a pin to our map.
 */ 
function addPinToMap(lat, lng, title, color) {
	if (!lat || !lng) {
		console.error("I need lat and long to place a pin");
		return;
	}
	
	$('#g_map').show();
	
	// request marker images
	var pinImage = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2" + (color ? '|' + color : ''),
		new google.maps.Size(21, 34),
		new google.maps.Point(0,0),
		new google.maps.Point(10, 34)
	);
	
	// place the marker
	var pin = new google.maps.Marker({
		map: g_map,
		position: new google.maps.LatLng(lat, lng),
		title: title,
		icon: pinImage
	});
	
	g_pins.push(pin);
	return pin;
}

/**
 *  Highlight the given pin and un-highlights other pins.
 */
function highlightPin(pin) {
	if (!pin) {
		console.error("I need a pin to highlight");
		return;
	}
	
	if (g_highlighted_pin) {
		g_highlighted_pin.setAnimation();
	}
	
	pin.setAnimation(google.maps.Animation.BOUNCE);
	g_highlighted_pin = pin;
}

/**
 *  Clears all pins.
 */
function clearAllPins() {
	for (var i = 0; i < g_pins.length; i++) {
		g_pins[i].setMap(null);
	};
	g_pins = [];
}
