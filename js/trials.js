/**
 *  Function for trial searching, fetching and listing.
 */

var _patient_loc = null;
var _trialSearchInterval = null;


/**
 *  Entry function to trial search
 */
function searchTrials(prob_name, gender, age) {
	_initTrialSearch(prob_name, gender, age);
}


function _initTrialSearch(problem_name, gender, age) {
	if (_trialSearchInterval) {
		console.warn('Already searching');
		return;
	}
	
	clearAllPins();
	_showTrialStatus('Starting...');
	
	$.ajax({
		'url': 'trial_runs',
		'data': {
			'cond': problem_name,
			'gender': gender,
			'age': age
		}
	})
	.always(function(obj1, status, obj2) {
		if ('success' == status) {
			if (_trialSearchInterval) {
				window.clearInterval(_trialSearchInterval);
			}
			_trialSearchInterval = window.setInterval(function() { _checkTrialStatus(obj1); }, 1000);
		}
		else {
			console.error(obj1, ' -- ', status, ' -- ', obj2);
			_showTrialStatus('Error, see console');
		}
	});
}


/**
 *  This function is called at an interval, checking server side progress until the server signals "done".
 */
function _checkTrialStatus(run_id) {
	$.ajax({
		'url': 'trial_runs/' + run_id + '/progress'
	})
	.always(function(obj1, status, obj2) {
		if ('success' == status) {
			
			// the run is done, get results
			if ('done' == obj1) {
				window.clearInterval(_trialSearchInterval);
				_trialSearchInterval = null;
				
				_showTrialStatus('Retrieving results...');
				_getTrialResults(run_id);
			}
			
			// an error occurred
			else {
				if (obj1 && obj1.length > 5 && obj1.match(/^error/i)) {
					window.clearInterval(_trialSearchInterval);
					_trialSearchInterval = null;
				}
				
				_showTrialStatus(obj1);
			}
		}
		else {
			console.error(obj1, status, obj2);
			_showTrialStatus('Error checking trial status, see console');
			window.clearInterval(_trialSearchInterval);
			_trialSearchInterval = null;
		}
	});
}

function _getTrialResults(run_id) {
	$.ajax({
		'url': 'trial_runs/' + run_id + '/results',
		'dataType': 'json'
	})
	.always(function(obj1, status, obj2) {
		if ('success' == status) {
			_showTrialStatus('Found ' + obj1.length + ' trials, filtering by demographics...');
			_filterTrialsByDemographics(run_id);
		}
		else {
			console.error(obj1, status, obj2);
			_showTrialStatus('Error getting trial results, see console');
		}
	});
}

function _filterTrialsByDemographics(run_id) {
	$.ajax({
		'url': 'trial_runs/' + run_id + '/filter/demographics',
		'dataType': 'json'
	})
	.always(function(obj1, status, obj2) {
		if ('success' == status) {
			_showTrialStatus('Filtering by problem list...');
			_filterTrialsByProblems(run_id);
		}
		else {
			console.error(obj1, status, obj2);
			_showTrialStatus('Error filtering trials (demographics), see console');
		}
	});
}

function _filterTrialsByProblems(run_id) {
	$.ajax({
		'url': 'trial_runs/' + run_id + '/filter/problems',
		'dataType': 'json'
	})
	.always(function(obj1, status, obj2) {
		if ('success' == status) {
			loadTrialsAfterLocatingPatient(obj1);
		}
		else {
			console.error(obj1, status, obj2);
			_showTrialStatus('Error filtering trials (problems), see console');
		}
	});
}


function loadTrialsAfterLocatingPatient(trial_tuples) {
	locatePatient(function(success, location) {
		if (success) {
			_patient_loc = location;
		}
		else {
			console.warn("Failed to locate the patient");
			_patient_loc = null;
		}
		
		// load the trials
		_loadTrials(trial_tuples);
	});
}

function _loadTrials(trial_tuples) {
	var main = $('#trials');
	var loader = $('<div/>', {'id': 'trial_loader'}).text('Loading trials...');
	main.empty().append(loader);
	
	var num_good = 0;
	var num_bad = 0;
	var opt_goodbad = $('<div/>').addClass('trial_opt_selector');
	var opt_location = $('<div/>').addClass('trial_opt_selector');
	var opt_type = $('<div/>').addClass('trial_opt_selector');
	var trial_list = $('<ul/>').addClass('trial_list');
	
	// loop all trials
	for (var i = 0; i < trial_tuples.length; i++) {
		var tpl = trial_tuples[i];
		var nct = tpl[0];
		var reason = null;
		if (tpl.length > 1) {
			reason = tpl[1];
			num_bad++;
		}
		else {
			num_good++;
		}
		
		// fetch trial details
		$.ajax({
			'url': 'trials/' + nct,
			'dataType': 'json',
			'context': {'reason': reason}
		})
		.always(function(obj1, status, obj2) {
			if ('success' == status) {
				
				// calculate distance and show locations on map
				if ('location' in obj1) {
					var distances = [];
					for (var j = 0; j < obj1.location.length; j++) {
						if ('geodata' in obj1.location[j]) {
							var lat = obj1.location[j].geodata.latitude;
							var lng = obj1.location[j].geodata.longitude;
							
							// distance
							if (_patient_loc) {
								var dist = kmDistanceBetweenLocations(_patient_loc, obj1.location[j].geodata);
								distances.push(dist);
								obj1.location[j].distance = dist;
							}
							else {
								console.warn("Patient location is not yet available");
							}
							
							// add pin with click handler
							var pin = addPinToMap(lat, lng, obj1.title, this.reason ? 'AA2200' : '33CC22');
							google.maps.event.addListener(pin, "click", function(e) {
    							
    							// on click, highlight and show the trial data
    							highlightPin(this);
    							$('#selected_trial').html('templates/trial_item.ejs', {'trial': obj1}).children(":first").addClass('active');
							});
						}
						else {
							console.warn("No geodata for trial location: ", obj1.location[j]);
						}
					}
					
					// get closest trial location
					if (distances.length > 0) {
						distances.sort(function(a, b) {
							return a - b;
						});
						
						obj1.closest = distances[0];
					}
				}
				else {
					console.warn("No geodata for trial " + nct);
				}
				
				// pull out intervention
				var types = [];
				if ('intervention' in obj1) {
					for (var j = 0; j < obj1.intervention.length; j++) {
						if ('intervention_type' in obj1.intervention[j]) {
							types.push(obj1.intervention[j].intervention_type);
						}
					}
					types = types.uniqueArray();
					
					// update types selector
					var existing = $.map(opt_type.children('a'), function(elem) {
						var my_type = $(elem).data('type');
						if (types.contains(my_type)) {
							var span = $(elem).find('span');
							span.text(span.text()*1 + 1);
						}
						return my_type;
					});
					
					// add the new ones
					for (var i = 0; i < types.length; i++) {
						var type = types[i];
						if (!existing.contains(type)) {
							var elem = _getOptTabElement(type, 1);
							elem.data('type', type);
							opt_type.append(elem);
						}
					};
				}
							
				// show in appropriate list
				$('#trial_loader').remove();
				
				obj1.reason = this.reason;
				var li = $('<li/>').html('templates/trial_item.ejs', {'trial': obj1});
				li.data('good', !this.reason);
				li.data('distance', obj1.closest);
				li.data('intervention-types', types);
				
				trial_list.append(li);
				
				// sort the list continuously
				var li_items = trial_list.children('li').get();
				li_items.sort(function(a, b) {
					return $(a).data('distance') - $(b).data('distance');
				});
				$.each(li_items, function(idx, itm) { trial_list.append(itm); });
			}
			else {
				console.error(obj1, status, obj2);
			}
		});
	}
	
	// compose DOM
	opt_goodbad.append(_getOptTabElement('Potential Trials', num_good + ' of ' + trial_tuples.length));
	opt_goodbad.append(_getOptTabElement('Ineligible Trials', num_bad + ' of ' + trial_tuples.length));
	main.append(opt_goodbad);
	main.append(opt_location);
	main.append(opt_type);
	main.append(trial_list);
}

function _showTrialStatus(status) {
	$('#trials').empty().text(status);
}

function _getOptTabElement(main, accessory, click) {
	var elem = $('<a/>').text(main);
	elem.append($('<span/>').text(accessory));
	
	return elem;
}

