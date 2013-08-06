/**
 *  A trial.
 */


var Trial = can.Construct({
	
},
{
	reason: null,						// the reason why this trial is not suitable for the patient
	intervention_types: null,
	trial_phases: null,
	trial_locations: null,
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
	 *  Comment
	 */
	locations: function() {
		if (null === this.trial_locations) {
			var locs = [];
			for (var i = 0; i < this.location.length; i++) {
				var loc = this.location[i];
				var loc_parts = ('formatted' in loc.geodata && loc.geodata.formatted.length > 0) ? loc.geodata.formatted.split(/,\s+/) : ["Unknown"];
				var loc_country = loc_parts.pop();
				var loc_stat_m_recr = loc.status ? loc.status.match(/recruiting/i) : null;
				var loc_stat_m_not = loc.status ? loc.status.match(/not\s+[\w\s]*\s+recruiting/i) : null;
				
				var loc_contact = 'contact' in loc && loc.contact ? loc.contact : null;
				if (!loc_contact || ((! ('email' in loc_contact) || !loc_contact.email) && (! ('phone' in loc_contact) || !loc_contact.phone))) {
					loc_contact = 'contact_backup' in loc && loc.contact_backup ? loc.contact_backup : null;
				}
				if (!loc_contact || ((! ('email' in loc_contact) || !loc_contact.email) && (! ('phone' in loc_contact) || !loc_contact.phone))) {
					loc_contact = 'overall_contact' in this ? this.overall_contact : null;
				}
				
				var loc_dict = {
					'name': ('facility' in loc && loc.facility.name) ? loc.facility.name : '',
					'city': (loc_parts.length > 0) ? loc_parts.join(', ') : '',
					'country': loc_country,
					'geodata': ('geodata' in loc ? loc.geodata : null),
					'status': loc.status,
					'status_color': loc_stat_m_not ? 'orange' : (loc_stat_m_recr ? 'green' : 'red'),
					'contact': loc_contact
				}
				
				locs.push(new TrialLocation(loc_dict));
			}
			
			this.trial_locations = locs;
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
		for (var i = 0; i < locs.length; i++) {
			var loc = locs[i];
			by_dist.push([loc.kmDistanceTo(to_location), loc]);
		}
		
		by_dist.sort(function(a, b) { return a[0] - b[0]; });
		this.last_loc_distances = by_dist;
		
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
	 *  @param elem The trial view element, locations will be added to a child div
	 *  @param start The start index, can be used to incrementally add locations
	 *  @param num The number of locations to add, will round up if less than 3 are left
	 *  @param animated Whether to animate blend-in, DOES NOT YET WORK
	 */
	showClosestLocations: function(elem, start, num, animated) {
		var loc_elem = elem.find('.trial_locations');
		var locs = this.locationsByDistance();
		
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
				var loc = locs[i][1];			// the list has tuples, distance and the location object
				var fragment = can.view('templates/trial_location.ejs', {'loc': loc});
				loc_elem.append(fragment);
			}
			
			// show link to show the next batch
			if (i < locs.length) {
				var next = Math.min(10, locs.length - i);
				
				var link = $('<a/>', {'href': 'javascript:void(0)'})
				.text('Show ' + ((next < locs.length - i) ? 'next ' + next : ' all'))
				.click(function(evt) {
					var trial = elem.data('trial');
					if (trial) {
						trial.showClosestLocations(elem, i, next, true);
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
	}
});

