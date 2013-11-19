/**
 *  Functions for Geo-Coding.
 */

var g_map = null;
var g_geocoder = null;
var g_clusterer = null;

var g_pins = [];
var g_highlighted_pin = null;
var g_patient_pin = null;
var g_patient_location = null;

var g_marker_green = null;
var g_marker_red = null;



/**
 *  Initially creates the map object
 */
function _geo_initMap() {
	if (g_map) {
		return;
	}
	
	// init map
	var mapOptions = {
		zoom: 4,
		minZoom: 3,
		maxZoom: 15,
		// center: new google.maps.LatLng(42.358, -71.06),		// Boston
		center: new google.maps.LatLng(38.5, -96.5),			// ~USA
		mapTypeId: google.maps.MapTypeId.ROADMAP
	};
	g_map = new google.maps.Map($("#g_map").get(0), mapOptions);
	
	// init clusterer (REMEMBER we have MODIFIED MarkerClusterer 2.0.9!)
	g_clusterer = new MarkerClusterer(g_map);
	g_clusterer.onClick = function(clickedClusterIcon) { 
		return _geo_multipleMarkersAtSameLocation(clickedClusterIcon.cluster_); 
	};
	
	// markers
	g_marker_green = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|33CC22",
		new google.maps.Size(21, 34),
		new google.maps.Point(0,0),
		new google.maps.Point(10, 34)
	);
	g_marker_red = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|AA2200",
		new google.maps.Size(21, 34),
		new google.maps.Point(0,0),
		new google.maps.Point(10, 34)
	);
	
	// zoom to patient if we have the location
	if (g_patient_location) {
		_geo_zoomToPatient();
	}
}

/**
 *  Shows the map div after setting its height to 40% the window height
 */
function geo_showMap() {
	var h = Math.max(300, Math.round($(window).height() * 0.4));
	$('#g_map').css('height', h + 'px').show();
	
	if (!g_map) {
		_geo_initMap();
	}
}

/**
 *  Hide the map and unhighlight any pin
 */
function geo_hideMap() {
	$('#g_map').hide();
	geo_unhighlightPin();
}



/**
 *  Pulls out the location text from the "#demo_location" field and geocodes the location, passing it into the callback.
 *  The callback receives:
 *  - success (bool)
 *  - latitude (string)
 *  - longitude (string)
 *  The LatLng object gets put into the "g_patient_location" global variable.
 */
function geo_locatePatient(address, callback) {
	if (!address || 0 == address.length) {
		g_patient_location = null;
		if (callback) {
			callback(false, null, null);
		}
		return;
	}
	
	geo_codeAddress(address, function(success, location) {
		g_patient_location = location;
		
		// set marker and center map
		if (g_map && location) {
			_geo_zoomToPatient();
		}
		
		// callback
		if (callback) {
			callback(success, location ? location.lat() : null, location ? location.lng() : null);
		}
	});
}


/**
 *  Locate the address via Google and display in our map.
 *  The callback receives a flag whether the geocoding was successful and a LatLng object.
 */
function geo_codeAddress(address, callback) {
	if (!address) {
		console.warn("No address given, cannot geo-code");
		if (callback) {
			callback(false, null);
		}
		return;
	}
	
	// create coder and map if needed
	if (!g_geocoder) {
		g_geocoder = new google.maps.Geocoder();
	}
	
	// code!
	g_geocoder.geocode({
		'address': address
	},
	function(results, status) {
		var loc = null;
		if (google.maps.GeocoderStatus.OK == status) {
			loc = results[0].geometry.location;
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
 *  Adds the given pins to our map.
 */
function geo_addPins(pins, animated, click_func) {
	if (!pins || 0 === pins.length) {
		return;
	}
	
	// add all
	var markers = [];
	for (var i = 0; i < pins.length; i++) {
		var pin = pins[i];
		var marker = new google.maps.Marker({
			position: new google.maps.LatLng(pin.lat, pin.lng),
			trial: pin.trial,
			location: pin.location,
			title: pin.trial.title,
			icon: pin.reason ? g_marker_red : g_marker_green,
			animation: animated ? google.maps.Animation.DROP : null
		});
		markers.push(marker);
		// g_pins.push(marker);			// let the cluster handle zooming for now
		
		// add click handler
		if (click_func) {
			google.maps.event.addListener(marker, "click", click_func);
		}
	}
	
	g_clusterer.addMarkers(markers);
}

/**
 *  Highlight the given pin and un-highlights other pins.
 */
function geo_highlightPin(pin) {
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
 *  Called when multiple pins are at the same location.
 *
 *  This is in our MODIFIED MarkerCluster class, as per:
 *  http://stackoverflow.com/questions/3548920/google-maps-api-v3-multiple-markers-on-exact-same-spot
 */
function _geo_multipleMarkersAtSameLocation(cluster) {
	if (cluster.getMarkers().length > 1) {
		var markers = cluster.getMarkers();
		showTrialsforPins(markers);
		return false;
	}
	return true;
}


/**
 *  Unhighlight the currently highlighted pin, if any.
 */
function geo_unhighlightPin() {
	if (g_highlighted_pin) {
		g_highlighted_pin.setAnimation();
		g_highlighted_pin = null;
	}
}


/**
 *  Zooms the map to show the current position marker and at least some pins (if there are any)
 */
function geo_zoomToPins(fit_num) {
	// disabled for now
	return;
	
	if (!g_map || !$('#g_map').is(':visible')) {
		return;
	}
	
	if (!fit_num || fit_num < 1) {
		fit_num = 5;
	}
	
	var latlngs = [];
	
	// consider patient location
	if (g_patient_location) {
		latlngs.push(g_patient_location);
	}
	
	// fit closest x pins
	if (g_pins.length > 0) {
		if (!g_patient_location) {
			for (var i = 0; i < g_pins.length; i++) {
				latlngs.push(g_pins[i].getPosition());
			}
		}
		else {
			var ll_tuples = [];
			
			// put all positions in an array along with their distance from the patient so we can sort by distance later
			for (var i = 0; i < g_pins.length; i++) {
				var pos = g_pins[i].getPosition();
				var dist = kmDistanceBetweenLocations(g_patient_location, pos);
				ll_tuples.push([pos, dist]);
			}
			ll_tuples.sort(function(a, b) {
				return a[1] - b[1];
			});
			
			// add closest x
			for (var i = 0; i < Math.min(ll_tuples.length, fit_num); i++) {
				latlngs.push(ll_tuples[i][0]);
			}
		}
	}
	
	// too few locations, try to center and set the zoom
	if (latlngs.length < 2) {
		if (latlngs.length > 0) {
			g_map.setCenter(latlngs[0]);
		}
		g_map.setZoom(4);
		return;
	}
	
	// fit to bounds (thanks Google for letting me construct sw and ne by hand :P)
	var sw = new google.maps.LatLng(Math.min(latlngs[0].lat(), latlngs[1].lat()) - 1, Math.min(latlngs[0].lng(), latlngs[1].lng()));
	var ne = new google.maps.LatLng(Math.max(latlngs[0].lat(), latlngs[1].lat()) + 1, Math.max(latlngs[0].lng(), latlngs[1].lng()));
	var bounds = new google.maps.LatLngBounds(sw, ne);
	if (!bounds) {
		console.error("Failed to get a bounds object to zoom the map");
		return;
	}
	
	for (var i = 2; i < latlngs.length; i++) {
		bounds.extend(latlngs[i]);
	}
	
	// g_map.panToBounds(bounds);
	g_map.fitBounds(bounds);
}

/**
 *  Clears all pins.
 */
function geo_clearAllPins() {
	for (var i = 0; i < g_pins.length; i++) {
		g_pins[i].setMap(null);
	}
	g_pins = [];
	
	if (g_clusterer) {
		g_clusterer.clearMarkers();
	}
}


/**
 *  Adds a patient pin and centers the map on it
 */
function _geo_zoomToPatient() {
	if (!g_patient_location) {
		return;
	}
	
	if (!g_map) {
		console.error("No map, cannot zoom to patient");
		return;
	}
	
	// add marker after removing existing one
	if (g_patient_pin) {
		g_patient_pin.setMap(null);
	}
	g_patient_pin = new google.maps.Marker({
		map: g_map,
		position: g_patient_location
	});
	
	// center
	g_map.setCenter(g_patient_location);
}


/**
 *  Calculates earth surface distances between two lat/long pairs using the Haversine formula.
 */
function kmDistanceBetweenLocationsLatLng(lat1, lng1, lat2, lng2) {
	var R = 6371;									// Radius of the earth in km
	var dLat = _geo_deg2rad(lat2 - lat1);
	var dLon = _geo_deg2rad(lng2 - lng1); 
	var a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(_geo_deg2rad(lat1)) * Math.cos(_geo_deg2rad(lat2)) * Math.sin(dLon/2) * Math.sin(dLon/2);
	var c = 2 * Math.asin(Math.sqrt(a));
	
	return R * c;
}

function kmDistanceBetweenLocations(l1, l2) {
	return kmDistanceBetweenLocationsLatLng(l1.lat(), l1.lng(), l2.lat(), l2.lng());
}

function _geo_deg2rad(deg) {
	return deg * (Math.PI / 180)
}



/**
 *  Enhancements to MarkerCluster (resolution to having multiple objects at the same location)
 */
MarkerClusterer.prototype.onClick = function() { 
    return true; 
};

