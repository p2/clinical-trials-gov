/**
 *  Functions for Geo-Coding.
 */

var g_map = null;
var g_geocoder = null;

var g_pins = [];
var g_highlighted_pin = null;


/**
 *  Pulls out the location text from the "#demo_location" field and geocodes the location, passing it into the callback.
 */
function locatePatient(callback) {
	var adr = $('#demo_location').val();
	if (adr) {
		geocodeAddress(adr, callback);
		return;
	}
	
	console.warn("Cannot locate patient, no address given");
	if (callback) {
		callback(false, null);
	}
}

function showMap() {
	$('#g_map').show();
}

function hideMap() {
	$('#g_map').hide();
}

/**
 *  Locate the address via Google and display in our map.
 *  The callback receives a flag whether the geocoding was successful and a lat/long object.
 */
function geocodeAddress(address, callback) {
	if (!address) {
		console.error("No address given, cannot geo-code");
		if (callback) {
			callback(false, null);
		}
		return;
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
		var loc = null;
		
		if (google.maps.GeocoderStatus.OK == status) {
			loc = {
				'latitude': results[0].geometry.location['jb'],
				'longitude': results[0].geometry.location['kb']
			};
			
			// center map and add a pin
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
		
		if (callback) {
			callback(loc != null, loc);
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


/**
 *  Calculates earth surface distances between two lat/long pairs using the Haversine formula.
 */
function kmDistanceBetweenLocations(l1, l2) {
	var R = 6371;										// Radius of the earth in km
	var dLat = deg2rad(l2.latitude - l1.latitude);
	var dLon = deg2rad(l2.longitude - l1.longitude); 
	var a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(deg2rad(l1.latitude)) * Math.cos(deg2rad(l2.latitude)) * Math.sin(dLon/2) * Math.sin(dLon/2);
	var c = 2 * Math.asin(Math.sqrt(a));
	
	return R * c;
}

function deg2rad(deg) {
	return deg * (Math.PI / 180)
}
