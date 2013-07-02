/**
 *  Function for trial searching, fetching and listing.
 */

var _patient_loc = null;
var _trialSearchInterval = null;

var _trialNumExpected = 0;
var _trialNumDone = 0;
var _showGoodTrials = true;
var _activeInterventionTypes = [];


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
	$('#trials').empty();
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
	_showTrialStatus("Loading " + trial_tuples.length + "trial" + (1 == trial_tuples.length ? "s" : '') + "...");
	
	var num_good = 0;
	var num_bad = 0;
	var opt_goodbad = $('<div/>', {'id': 'selector_goodbad'}).addClass('trial_opt_selector');
	var opt_location = $('<div/>', {'id': 'selector_location'}).addClass('trial_opt_selector');
	var opt_type = $('<div/>', {'id': 'selector_inv_type'}).addClass('trial_opt_selector');
	var trial_list = $('<ul/>', {'id': 'trial_list'}).addClass('trial_list');
	
	_trialNumExpected = trial_tuples.length;
	_trialNumDone = 0;
	_showGoodTrials = true;
	_activeInterventionTypes = [];
	
	// loop all trials
	for (var i = 0; i < trial_tuples.length; i++) {
		var tpl = trial_tuples[i];
		var nct = tpl[0];
		var reason = null;
		if (tpl.length > 1) {
			reason = tpl[1];
			if (reason) {
				num_bad++;
			}
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
			
			// update status
			_trialNumDone++;
			if (_trialNumDone >= _trialNumExpected) {
				_showTrialStatus();
			}
			else {
				_showTrialStatus("Loading, " + Math.round(_trialNumDone / _trialNumExpected * 100) + "% done...");
			}
			
			if ('success' == status) {
				obj1.reason = this.reason;
				
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
				}
				
				if (types.length < 1) {
					types = ['N/A'];
				}
				
				// update types selector
				var existing = $.map(opt_type.children('a'), function(elem) {
					var my_type = $(elem).data('intervention-type');
					if (!obj1.reason && types.contains(my_type)) {		// initial display is good trials only, so only count if we are a good trial
						var span = $(elem).find('.num_matches');
						span.text(span.text()*1 + 1);
					}
					return my_type;
				});
				
				// add the new ones
				for (var i = 0; i < types.length; i++) {
					var type = types[i];
					if (!existing.contains(type)) {
						var elem = _getOptTabElement(type, obj1.reason ? 0 : 1, _toggleInterventionType);
						elem.data('intervention-type', type);
						opt_type.append(elem);
					}
				};
				
				// sort types alphabetically
				sortChildren(opt_type, 'a', function(a, b) {
					return $(a).text().toLowerCase().localeCompare($(b).text().toLowerCase());
				});
				
				// add to list
				var li = $('<li/>').html('templates/trial_item.ejs', {'trial': obj1});
				li.hide();
				li.data('good', !this.reason);
				li.data('distance', obj1.closest);
				li.data('intervention-types', types);
				
				trial_list.append(li);
				
				// sort the list continuously by distance
				sortChildren(trial_list, 'li', function(a, b) {
					return $(a).data('distance') - $(b).data('distance');
				});
			}
			else {
				console.error(obj1, status, obj2);
			}
		});
	}
	
	// compose DOM
	var good_trials = _getOptTabElement('Potential Trials', num_good + ' of ' + trial_tuples.length, _toggleShowGoodTrials);
	good_trials.addClass('active');
	good_trials.data('is-good', true);
	opt_goodbad.append(good_trials);
	
	var bad_trials = _getOptTabElement('Ineligible Trials', num_bad + ' of ' + trial_tuples.length, _toggleShowGoodTrials);
	bad_trials.data('is-good', false);
	opt_goodbad.append(bad_trials);
	
	main.append(opt_goodbad);
	main.append(opt_location);
	main.append(opt_type);
	main.append('<div class="supplement">A trial can have more than one intervention type.</div>');
	main.append(trial_list);
}


/**
 *  Display the current trial loading status (or hide it if status is null)
 */
function _showTrialStatus(status) {
	var stat = $('#trial_status');
	if (!status) {
		stat.remove();
		return;
	}
	
	if (!stat.is('*')) {
		stat = $('<div/>', {'id': 'trial_status'});
		$('#trials').append(stat);
	}
	stat.text(status);
}

function _getOptTabElement(main, accessory, click) {
	var elem = $('<a/>', {'href': 'javascript:void(0)'});
	elem.append($('<span/>').text(main));
	elem.append($('<span/>').addClass('num_matches').text(accessory));
	if (click) {
		elem.click(click);
	}
	
	return elem;
}


function _toggleShowGoodTrials(evt) {
	_showGoodTrials = !_showGoodTrials;
	_updateShownHiddenTrials();
}

function _toggleInterventionType(evt) {
	var type = $(this).data('intervention-type');
	if (!type) {
		console.error("No type supplied to _toggleInterventionType()");
		return;
	}
	
	// toggle
	var idx = _activeInterventionTypes.indexOf(type);
	if (idx >= 0) {
		_activeInterventionTypes.splice(idx, 1);
	}
	else {
		_activeInterventionTypes.push(type);
	}
	
	_updateShownHiddenTrials();
}

/**
 *  Loops all trials and shows or hides according to our globals.
 */
function _updateShownHiddenTrials() {
	var per_type = {};
	
	$('#trial_list').children('li').each(function(idx, item) {
		var elem = $(item);
		
		// good or bad
		var show = (_showGoodTrials == elem.data('good'));
		
		// intervention type
		if (show) {
			var types = elem.data('intervention-types');
			show = _activeInterventionTypes.intersects(types);
			for (var i = 0; i < types.length; i++) {
				if (types[i] in per_type) {
					per_type[types[i]]++;
				}
				else {
					per_type[types[i]] = 1;
				}
			};
		}
		
		// apply
		if (show) {
			elem.slideDown('fast');
		}
		else {
			elem.slideUp('fast');
		}
	});
	
	// update good/bad selector
	$('#selector_goodbad').children('a').each(function(idx, item) {
		var elem = $(item);
		elem.removeClass('active');
		if (_showGoodTrials == elem.data('is-good')) {
			elem.addClass('active');
		}
	});
	
	// update intervention type selector
	$('#selector_inv_type').children('a').each(function(idx, item) {
		var elem = $(item);
		var type = elem.data('intervention-type');
		elem.find('.num_matches').text(type in per_type ? per_type[type] : 0);
		
		elem.removeClass('active');
		if (_activeInterventionTypes.contains(type)) {
			elem.addClass('active');
		}
	});
}

