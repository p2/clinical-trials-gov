/**
 *  A trial location.
 */


var TrialLocation = can.Construct({
	
},
{
	distance: null,
	
	init: function(json) {
		for (var key in json) {
		    if (json.hasOwnProperty(key)) {
		        this[key] = json[key];
		    }
		}
	},
	
	
	kmDistanceTo: function(to_location) {
		if (to_location && 'geodata' in this) {
			this.distance = kmDistanceBetweenLocationsLatLng(to_location.lat(), to_location.lng(), this.geodata.latitude, this.geodata.longitude);
		}
		else if (to_location) {
			console.warn("No geodata for trial location: ", this);
			this.distance = null;
		}
		
		return this.distance;
	}
});


/**
 *  Shows or hides the contact info for one trial location.
 */
function _toggleTrialLocationContact(elem) {
	var link = $(elem);
	var loc = link.siblings('.loc_contact');
	
	// hide
	if (loc.is(':visible')) {
		loc.fadeOut('fast');
	}
	
	// show (and align)
	else {
		loc.show();
		loc.css('left', (link.outerWidth() - loc.outerWidth()) / 2 + link.position().left);
	}
}
