/**
 *  A trial.
 */


var Trial = can.Construct({
	
	/**
	 *  Geocode an array of trials.
	 */
	geocode: function(trials, to_location) {
		for (var i = 0; i < trials.length; i++) {
			trials[i].geocode(to_location);
		}
	}
},
{
	reason: null,						// the reason why this trial is not suitable for the patient
	intervention_types: null,
	trial_phases: null,
	trial_locations: null,
	did_add_pins: false,
	last_loc_distances: null,
	closest: null,
	
	init: function(json) {
		for (var key in json) {
		    if (json.hasOwnProperty(key)) {
		        this[key] = json[key];
		    }
		}
	},
	
	
	/**
	 *  Return intervention types of the trial.
	 */
	interventionTypes: function() {
		if (null == this.intervention_types) {
			var types = [];
			if ('intervention' in this && this.intervention) {
				for (var i = 0; i < this.intervention.length; i++) {
					if ('intervention_type' in this.intervention[i]) {
						types.push(this.intervention[i].intervention_type);
					}
				}
				types = types.uniqueArray();
			}
			
			if (types.length < 1) {
				types = ['Observational'];
			}
			
			this.intervention_types = types;
		}
		
		return this.intervention_types;
	},
	
	
	/**
	 *  Trial phases.
	 */
	trialPhases: function() {
		if (null == this.trial_phases) {
			if (!'phase' in this || !this.phase) {
				this.phase = 'N/A';
			}
			
			var phases = ['N/A'];
			if ('N/A' != this.phase) {
				phases = this.phase.split('/');
			}
			this.trial_phases = phases;
		}
		
		return this.trial_phases;
	},
	
	
	/**
	 *  Get the trial's recruitment locations.
	 *  TODO: Move the logic into trial_location.js
	 */
	locations: function() {
		if (null === this.trial_locations) {
			if ('location' in this && this.location) {
				var locs = [];
				for (var i = 0; i < this.location.length; i++) {
					var loc = this.location[i];
					var loc_parts = ('formatted' in loc.geodata && loc.geodata.formatted && loc.geodata.formatted.length > 0) ? loc.geodata.formatted.split(/,\s+/) : ["Unknown"];
					var loc_country = loc_parts.pop();
					var loc_stat_m_recr = loc.status ? loc.status.match(/recruiting/i) : null;
					var loc_stat_m_not = loc.status ? loc.status.match(/not\s+[\w\s]*\s+recruiting/i) : null;
					
					var loc_dict = {
						'trial': this,
						'name': ('facility' in loc && loc.facility.name) ? loc.facility.name : '',
						'city': (loc_parts.length > 0) ? loc_parts.join(', ') : '',
						'country': loc_country,
						'geodata': ('geodata' in loc ? loc.geodata : null),
						'status': loc.status,
						'status_color': loc_stat_m_not ? 'orange' : (loc_stat_m_recr ? 'green' : 'red'),
						'contact': ('contact' in loc && loc.contact) ? loc.contact : null
					}
					
					locs.push(new TrialLocation(loc_dict));
				}
				
				this.trial_locations = locs;
			}
		}
		
		return this.trial_locations;
	},
	
	/**
	 *  Sorts the trial locations by distance to the given location object and returns an array with distance-location tuples.
	 */
	locationsByDistance: function(to_location) {
		if (!to_location && null !== this.last_loc_distances) {
			return this.last_loc_distances;
		}
		
		var by_dist = [];
		var locs = this.locations();
		if (locs) {
			for (var i = 0; i < locs.length; i++) {
				var loc = locs[i];
				by_dist.push([loc.kmDistanceTo(to_location), loc]);
			}
			
			by_dist.sort(function(a, b) { return a[0] - b[0]; });
			this.last_loc_distances = by_dist;
		}
		return by_dist;
	},
	
	
	/**
	 *  Geocodes the trial
	 */
	geocode: function(to_location) {
		var distances = this.locationsByDistance(to_location);
		var closest = (distances && distances.length > 0) ? distances[0] : [99999,null];
		
		this.closest = closest[0];
	},
	
	
	/**
	 *  Adds the next x locations to the trial view.
	 *  @param to_location The location to measure the distance to
	 *  @param elem The trial view element, locations will be added to a child div
	 *  @param start The start index, can be used to incrementally add locations
	 *  @param num The number of locations to add, will round up if less than 3 are left
	 *  @param animated Whether to animate blend-in, DOES NOT YET WORK
	 */
	showClosestLocations: function(to_location, elem, start, num, animated) {
		var loc_elem = elem.find('.trial_locations');
		var locs = this.locations();
		// var locs = this.locationsByDistance(to_location);	// locations() are ordered on the server already
		
		// add locations
		if (locs && locs.length > 0) {
			loc_elem.find('.show_more_locations').remove();
			
			// determine max number (if we're within 2 of the maximum we show all)
			var max = Math.min(locs.length - start, num);
			if (locs.length - start - max < 3) {
				max = locs.length - start;
			}
			max += start;
			
			// show desired ones
			var i = start;
			for (; i < max; i++) {
				var loc = locs[i];
				// var loc = locs[i][1];			// the list has tuples, distance and the location object, if we use "locationsByDistance"
				loc.kmDistanceTo(to_location);
				var fragment = can.view('templates/trial_location.ejs', {'loc': loc});
				loc_elem.append(fragment);
			}
			
			// show link to show the next batch
			if (i < locs.length) {
				var trial = this;
				var n_max = 10;
				var next = (locs.length - i - n_max < 3) ? locs.length - i : n_max;
				
				var link = $('<a/>', {'href': 'javascript:void(0)'})
				.text('Show ' + ((next < locs.length - i) ? 'next ' + next : ' all'))
				.click(function(evt) {
					if (trial) {
						trial.showClosestLocations(to_location, elem, i, next, true);
					}
					else {
						console.error("The trial object is undefined");
					}
				});
				
				var div = $('<div/>').addClass('trial_location').addClass('show_more_locations');
				var h3 = $('<h3/>').html('There are ' + (locs.length - i) + ' more locations<br />');
				h3.append(link);
				div.append(h3);
				
				if (animated) {
					div.hide();
					loc_elem.append(div);
					div.fadeIn('fast');
				}
				else {
					loc_elem.append(div);
				}
			}
		}
		
		// no locations
		else {
			var div = $('<div class="trial_location"><h3>No trial locations available</h3></div>');
			loc_elem.append(div);
		}
	},
	
	/**
	 *  Show a single location.
	 */
	showLocation: function(elem, location) {
		var fragment = can.view('templates/trial_location.ejs', {'loc': location});
		elem.find('.trial_locations').append(fragment);
	},
	
	/**
	 *  Get pins for all locations.
	 */
	locationPins: function() {
		var locs = this.locations();
		var pins = [];
		
		if (locs && locs.length > 0) {
			
			for (var i = 0; i < locs.length; i++) {
				if ('geodata' in locs[i]) {
					var loc = {
						'lat': locs[i].geodata.latitude,
						'lng': locs[i].geodata.longitude,
						'location': locs[i],
						'trial': this
					};
					
					pins.push(loc);
				}
			}
		}
		
		return pins;
	}
});


/**
 *  Shows or hides the trial's eligibility criteria
 */
function _toggleEligibilityCriteria(elem) {
	var link = $(elem);
	var trial_elem = link.closest('.trial');
	var crit_elem = trial_elem.find('.formatted_criteria').first();
	
	// hide
	if (crit_elem.is(':visible')) {
		crit_elem.hide();
		link.text('Show eligibility criteria');
	}
	
	// show
	else {
		crit_elem.show();
		link.text('Hide eligibility criteria');
	}
}

