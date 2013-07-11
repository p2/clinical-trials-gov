/**
 *  Function for trial searching, fetching and listing.
 */

var _patient_loc = null;
var _trialSearchInterval = null;
var _trialSearchMustStop = false;

var _trialBatchSize = 25;
var _trialNumExpected = 0;
var _trialNumDone = 0;
var _showGoodTrials = true;
var _activeInterventionTypes = [];

var _shouldShowPinsForTrials = [];


/**
 *  Entry function to trial search
 */
function searchTrials(prob_name, gender, age, remember_cond) {
	_trialSearchMustStop = false;
	_initTrialSearch(prob_name, gender, age, remember_cond);
}

function cancelTrialSearch() {
	_showTrialStatus('Stopping...');
	_trialSearchMustStop = true;
	if (_trialSearchInterval) {
		window.clearInterval(_trialSearchInterval);
		_trialSearchInterval = null;
	}
}


function _initTrialSearch(problem_name, gender, age, remember_cond) {
	if (_trialSearchInterval) {
		console.warn('Already searching');
		return;
	}
	
	// prepare map and DOM
	clearAllPins();
	$('#trial_selectors').empty();
	$('#trials').empty();
	_showTrialStatus('Starting...');
	
	// fire off AJAX call
	$.ajax({
		'url': 'trial_runs',
		'data': {
			'cond': problem_name,
			'gender': gender,
			'age': age,
			'remember_cond': remember_cond ? true : false
		}
	})
	.always(function(obj1, status, obj2) {
		if (_trialSearchMustStop) {
			return;
		}
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
	
	// never forget
	if (remember_cond) {
		_last_manual_condition = problem_name;
	}
}


/**
 *  This function is called at an interval, checking server side progress until the server signals "done".
 */
function _checkTrialStatus(run_id) {
	$.ajax({
		'url': 'trial_runs/' + run_id + '/progress'
	})
	.always(function(obj1, status, obj2) {
		if (_trialSearchMustStop) {
			return;
		}
		
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
		if (_trialSearchMustStop) {
			return;
		}
		
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
		if (_trialSearchMustStop) {
			return;
		}
		
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
		if (_trialSearchMustStop) {
			return;
		}
		
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
	var adr = $('#demo_location').val();
	if (!adr) {
		console.warn("No patient location information, loading trials without distance information");
		_patient_loc = null;
		_loadTrials(trial_tuples);
		return;
	}
	
	// locate (asynchronously)
	locatePatient(adr, function(success, location) {
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
	if (!trial_tuples || trial_tuples.length < 1) {
		_showTrialStatus("There are no such trials");
		return;
	}
	
	_showTrialStatus("Loading " + trial_tuples.length + " trial" + (1 == trial_tuples.length ? "s" : '') + "...");
	$('#g_map_toggle').show();
	
	var num_good = 0;
	var num_bad = 0;
	var opt_goodbad = $('<div/>', {'id': 'selector_goodbad'}).addClass('trial_opt_selector');
	var opt_type = $('<div/>', {'id': 'selector_inv_type'}).addClass('trial_opt_selector');
	var trial_list = $('<ul/>', {'id': 'trial_list'}).addClass('trial_list');
	
	_trialNumExpected = trial_tuples.length;
	_trialNumDone = 0;
	_showGoodTrials = true;
	_activeInterventionTypes = [];
	
	// batch the trials
	var batch = {};
	var batches = [];
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
		
		// manage the batch
		batch[nct] = reason;
		if (0 == (i + 1) % _trialBatchSize || i == trial_tuples.length - 1) {
			batches.push(batch);
			batch = {};
		}
	}
	
	// fetch trial details
	for (var i = 0; i < batches.length; i++) {
		var batch = batches[i];
		var ncts = [];
		for (var nct in batch) {
			ncts.push(nct);
		}
		
		if (0 == ncts.length) {
			console.warn("There are no studies in this batch");
			continue;
		}
		
		// fetch
		$.ajax({
			'url': 'trials/' + ncts.join(':'),
			'dataType': 'json',
			'context': {'reasons': batch}
		})
		.always(function(obj1, status, obj2) {
			if (_trialSearchMustStop) {
				return;
			}
			
			// got trials
			if ('success' == status) {
				var type_dict = {};
				
				var trials = 'trials' in obj1 ? obj1.trials : [];
				for (var i = 0; i < trials.length; i++) {
					var trial = trials[i];
					
					// update status
					_trialNumDone++;
					if (_trialNumDone >= _trialNumExpected) {
						_showTrialStatus();
					}
					else {
						_showTrialStatus("Loading, " + Math.round(_trialNumDone / _trialNumExpected * 100) + "% done...");
					}
					
					trial.reason = this.reasons[trial.nct];
					_geocodeTrial(trial);
					
					// pull out intervention types
					var types = [];
					if ('intervention' in trial && trial.intervention) {
						for (var j = 0; j < trial.intervention.length; j++) {
							if ('intervention_type' in trial.intervention[j]) {
								types.push(trial.intervention[j].intervention_type);
							}
						}
						types = types.uniqueArray();
					}
					
					if (types.length < 1) {
						types = ['N/A'];
					}
					
					// collect all types (initially we only show the "good" trials, so don't count the bad ones in the dict)
					for (var j = 0; j < types.length; j++) {
						var type = types[j];
						if (type in type_dict) {
							type_dict[type] = type_dict[type] + (this.reason ? 0 : 1);
						}
						else {
							type_dict[type] = (this.reason ? 0 : 1);
						}
					}
					
					// add to list
					var li = $('<li/>').html('templates/trial_item.ejs', {'trial': trial});
					li.data('trial', trial);
					li.data('good', !this.reason);
					li.data('distance', trial.closest);
					li.data('intervention-types', types);
					
					trial_list.append(li);
				}
				
				// get the existing types and add the new ones
				var existing = $.map(opt_type.children('a'), function(elem) {
					var child_type = $(elem).data('intervention-type');
					if (child_type in type_dict) {		
						var span = $(elem).find('.num_matches');
						span.text(span.text()*1 + type_dict[child_type]);
					}
					return child_type;
				});
				
				for (var type in type_dict) {
					if (!existing.contains(type)) {
						var elem = _getOptTabElement(type, type_dict[type], _toggleInterventionType);
						elem.data('intervention-type', type);
						opt_type.append(elem);
					}
				}
				
				// sort types alphabetically
				sortChildren(opt_type, 'a', function(a, b) {
					return $(a).text().toLowerCase().localeCompare($(b).text().toLowerCase());
				});
				
				// sort the trial list by distance
				sortChildren(trial_list, 'li', function(a, b) {
					return $(a).data('distance') - $(b).data('distance');
				});
			}
			
			// error, make sure the counter is still accurate and log a warning
			else {
				_trialNumDone += this.reasons.length;
				if (_trialNumDone >= _trialNumExpected) {
					_showTrialStatus();
				}
				console.error("Failed loading NCTs:", ncts.join(', '), "obj1:", obj1, "obj2:", obj2);
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
	
	var opt = $('#trial_selectors');
	opt.append(opt_goodbad);
	opt.append('<div class="trial_opt_header"><b>Intervention types</b> <span class="supplement">(Trials can have more than one intervention type)</span></div>');
	opt.append(opt_type);
	
	$('#trials').append(trial_list);
}



/**
 *  Toggles the trial map
 */
function toggleTrialMap() {
	
	// hide
	if ($('#g_map').is(':visible')) {
		hideMap();
		$('#g_map_toggle').text('Show Map');
		$('#selected_trial').empty().hide();
	}
	
	// show
	else {
		showMap();
		$('#g_map_toggle').text('Hide Map');
		
		// pins
		if (_shouldShowPinsForTrials.length > 0) {
			for (var i = 0; i < _shouldShowPinsForTrials.length; i++) {
				_showPinsForTrial(_shouldShowPinsForTrials[i], false);
			};
		}
		zoomToPins();
	}
}

/**
 *  Geocodes one trial (if not already done)
 */
function _geocodeTrial(trial) {
	if ('closest' in trial) {
		// already coded
		return;
	}
	
	// need location information to geo-code
	if ('location' in trial) {
		var distances = [];
		for (var i = 0; i < trial.location.length; i++) {
			if ('geodata' in trial.location[i]) {
				
				// distance
				if (_patient_loc) {
					var dist = kmDistanceBetweenLocationsLatLng(_patient_loc.lat(), _patient_loc.lng(), trial.location[i].geodata.latitude, trial.location[i].geodata.longitude);
					distances.push(dist);
					trial.location[i].distance = dist;
				}
				else {
					console.warn("Patient location is not yet available");
				}
			}
			else {
				console.warn("No geodata for trial location: ", trial.location[i]);
			}
		}
		
		// get closest trial location
		if (distances.length > 0) {
			distances.sort(function(a, b) {
				return a - b;
			});
			
			trial.closest = distances[0];
		}
	}
	else {
		console.warn("No geodata for trial " + trial.nct);
	}
}


function _showPinsForTrial(trial, animated) {
	if (!trial) {
		console.error("No trial to show pins for");
		return;
	}
	
	if ('location' in trial) {
		for (var i = 0; i < trial.location.length; i++) {
			if ('geodata' in trial.location[i]) {
				var lat = trial.location[i].geodata.latitude;
				var lng = trial.location[i].geodata.longitude;
				
				addPinToMap(lat, lng, trial.title, trial.reason ? 'AA2200' : '33CC22', animated, function(e) {
					highlightPin(this);
					showSelectedTrial(trial);
				});
			}
		}
	}
}

function showSelectedTrial(trial) {
	$('#selected_trial').show().html('templates/trial_item.ejs', {'trial': trial}).children(":first").addClass('active');
	$('#selected_trial').append('<a class="dismiss_link" href="javascript:void(0);" onclick="unloadSelectedTrial()">dismiss</a>');
}

function unloadSelectedTrial() {
	$('#selected_trial').slideUp('fast', function() { $(this).empty(); });
	unhighlightPin();
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
		$('#trial_selectors').append(stat);
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
	var hasMap = $('#g_map').is(':visible');
	
	// clean up pins
	clearAllPins();
	_shouldShowPinsForTrials = [];
	$('#selected_trial').empty();
	
	// loop all trials and show or hide them accordingly
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
			if (hasMap) {
				_showPinsForTrial(elem.data('trial'), !elem.is(':visible'));
			}
			else {
				_shouldShowPinsForTrials.push(elem.data('trial'));
			}
			elem.slideDown('fast');
		}
		else {
			elem.slideUp('fast');
		}
	});
	
	window.setTimeout(zoomToPins, 100);
	
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

