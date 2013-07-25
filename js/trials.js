/**
 *  Function for trial searching, fetching and listing.
 */

var _patient_loc = null;
var _trialSearchInterval = null;
var _trialSearchMustStop = false;

var _trialBatchSize = 10;		// 25 might be too much for some computers
var _trialNumExpected = 0;
var _trialNumDone = 0;
var _showGoodTrials = true;

var _shouldShowPinsForTrials = [];


/**
 *  Entry function to trial search
 */
function searchTrials(prob_name, gender, age, remember_cond) {
	_trialSearchMustStop = false;
	_initTrialSearch(prob_name, gender, age, remember_cond);
}

function cancelTrialSearch() {
	_trialSearchMustStop = true;
	if (_trialSearchInterval) {
		window.clearInterval(_trialSearchInterval);
		_trialSearchInterval = null;
	}
	
	_showTrialStatus();
	resetUI();
}

function resetUI() {
	_hideNoTrialsHint()
	
	$('#trial_selectors').find('.trial_selector').empty();
	$('#trial_selectors').find('.trial_opt_selector > ul').empty();
	$('#trial_selectors').hide();
	$('#trial_list').empty();
	
	clearAllPins();
	hideMap();
	$('#g_map_toggle').hide();
}


function _initTrialSearch(problem_name, gender, age, remember_cond) {
	if (_trialSearchInterval) {
		console.warn('Already searching');
		return;
	}
	
	// reset UI
	resetUI();
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
			_showTrialStatus('Error searching for trials: ' + status + ', see console');
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
	
	_showTrialStatus("Loading " + trial_tuples.length + " trial" + (1 == trial_tuples.length ? "" : "s") + "...");
	$('#g_map_toggle').show();
	
	_trialNumExpected = trial_tuples.length;
	_trialNumDone = 0;
	_showGoodTrials = true;
	
	// batch the trials
	var batch = {};
	var batches = [];
	
	var num_good = 0;
	var num_bad = 0;
	
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
	
	// add the trial type selector
	var opt_goodbad = $('#selector_goodbad');
	var good_trials = _getOptRadioElement('Potential Trials', num_good + ' of ' + trial_tuples.length, true);
	good_trials.data('is-good', true);
	opt_goodbad.append(good_trials);
	
	var bad_trials = _getOptRadioElement('Ineligible Trials', num_bad + ' of ' + trial_tuples.length, false);
	bad_trials.data('is-good', false);
	opt_goodbad.append(bad_trials);
	
	// fire off!
	_loadTrialBatchContinuing(batches, -1, []);
}


/**
 *  Fetches the given batch of studies, does all the magic and calls itself until all batches have been loaded
 */
function _loadTrialBatchContinuing(batches, previous, intervention_types, drug_phases) {
	var current = previous + 1;
	if (!batches || current >= batches.length) {
		console.warn("We should have stopped, there's no batch number " + current + " in these batches: ", batches);
		return;
	}
	if (_trialSearchMustStop) {
		return;
	}
	
	if (!intervention_types) {
		intervention_types = [];
	}
	if (!drug_phases) {
		drug_phases = [];
	}
	
	var batch = batches[current];
	var ncts = [];
	for (var nct in batch) {
		ncts.push(nct);
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
		var cont = true;
		
		// got trials
		if ('success' == status) {
			var trial_list = $('#trial_list');
			var type_arr = [];
			
			// loop trials
			var trials = 'trials' in obj1 ? obj1.trials : [];
			for (var i = 0; i < trials.length; i++) {
				var trial = trials[i];
				
				// update status
				_trialNumDone++;
				if (_trialNumDone >= _trialNumExpected) {
					cont = false;
					_showTrialStatus();
				}
				else {
					var percent = Math.round(_trialNumDone / _trialNumExpected * 100);
					if (percent >= 99) {
						_showTrialStatus("Almost there...");
					}
					else {
						_showTrialStatus("Loading, " + percent + "% done...");
					}
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
					types = ['Observational'];
				}
				intervention_types = intervention_types.concat(types);
				
				// pull out trial phase
				if (!'phase' in trial || !trial.phase) {
					trial.phase = 'N/A';
				}
				var phases = ['N/A'];
				if ('N/A' != trial.phase) {
					phases = trial.phase.split('/');
				}
				drug_phases = drug_phases.concat(phases);
				
				// add the trial to the list
				var li = $('<li/>').html('templates/trial_item.ejs', {'trial': trial});
				li.data('trial', trial);
				li.data('good', !trial.reason);
				li.data('distance', trial.closest);
				li.data('intervention-types', types);
				li.data('phases', phases);
				
				trial_list.append(li);
			}
		}
		
		// error, make sure the counter is still accurate and log a warning
		else {
			_trialNumDone += this.reasons.length;
			if (_trialNumDone >= _trialNumExpected) {
				_showTrialStatus();
			}
			console.error("Failed loading NCTs:", ncts.join(', '), "obj1:", obj1, "obj2:", obj2);
		}
		
		// finish or fetch next
		if (cont) {
			_loadTrialBatchContinuing(batches, current, intervention_types, drug_phases);
		}
		else {
			_didLoadTrialBatches(batches, intervention_types, drug_phases);
		}
	});
}


/**
 *  Called when the last batch has been loaded.
 *
 *  Note that intervention_types and drug_phases possibly contains many duplicates.
 */
function _didLoadTrialBatches(batches, intervention_types, drug_phases) {
	_showNoTrialsHint();
	
	// add all intervention types
	if (intervention_types) {
		intervention_types = intervention_types.uniqueArray();
		var opt_type = $('#selector_inv_type');
		
		for (var i = 0; i < intervention_types.length; i++) {
			var type = intervention_types[i];
			var elem = _getOptCheckElement(type, 0, false);
			elem.data('intervention-type', type);
			opt_type.append(elem);
		}
		
		// sort types alphabetically
		sortChildren(opt_type, 'li', function(a, b) {
			return $(a).text().toLowerCase().localeCompare($(b).text().toLowerCase());
		});
	}
	
	// add phases to the phase list
	if (drug_phases) {
		drug_phases = drug_phases.uniqueArray();
		var opt_phase = $('#selector_inv_phase');
		
		for (var i = 0; i < drug_phases.length; i++) {
			var phase = drug_phases[i];
			var elem = _getOptCheckElement(phase, 0, true);
			elem.data('phase', phase);
			opt_phase.append(elem);
		}
		
		// sort phases alphabetically
		sortChildren(opt_phase, 'li', function(a, b) {
			return $(a).text().toLowerCase().localeCompare($(b).text().toLowerCase());
		});
	}
	
	// sort the trial list by distance
	sortChildren($('#trial_list'), 'li', function(a, b) {
		return $(a).data('distance') - $(b).data('distance');
	});
	
	$('#trial_selectors').show();
	$('#trials').show();
	_updateShownHiddenTrials();
	_showTrialStatus();
}


function _getOptRadioElement(main, accessory, active) {
	var elem = $('<li/>', {'href': 'javascript:void(0)'});
	var uuid = newUUID();
	var input = $('<input/>', {'id': uuid, 'type': 'radio', 'name': 'ugly_hack'});
	input.change(_toggleShowGoodTrials);
	
	elem.append(input);
	elem.append($('<label/>', {'for': uuid}).text(main));
	elem.append($('<span/>').addClass('num_matches').text(accessory));
	
	if (active) {
		elem.addClass('active');
		input.attr('checked', true);
	}
	
	return elem;
}

function _getOptCheckElement(main, accessory, active) {
	var elem = $('<li/>', {'href': 'javascript:void(0)'});
	var uuid = newUUID();
	var input = $('<input/>', {'id': uuid, 'type': 'checkbox'});
	elem.append(input);
	elem.append($('<label/>', {'for': uuid}).text(main));
	elem.append($('<span/>').addClass('num_matches').text(accessory));
	
	input.change(_toggleOptCheckElement);
	
	if (active) {
		elem.addClass('active');
		input.attr('checked', true);
	}
	
	return elem;
}



function _toggleShowGoodTrials(evt) {
	_showGoodTrials = !_showGoodTrials;
	_updateShownHiddenTrials();
}


function _toggleOptCheckElement(evt) {
	var elem = $(this).parent();
	
	// toggle class by input checked status
	if (elem.find('input').prop('checked')) {
		elem.addClass('active');
	}
	else {
		elem.removeClass('active');
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
	
	// get active intervention types
	var active_types = [];
	$('#selector_inv_type').children('li').each(function(idx, item) {
		var elem = $(item);
		if (elem.hasClass('active')) {
			active_types.push(elem.data('intervention-type'));
		}
	});
	
	// get active phases
	var active_phases = [];
	$('#selector_inv_phase').children('li').each(function(idx, item) {
		var elem = $(item);
		if (elem.hasClass('active')) {
			active_phases.push(elem.data('phase'));
		}
	});
	
	// loop all trials and show or hide them accordingly
	var num_shown = 0;
	var num_w_phase = 0;
	var per_type = {};
	var per_phase = {};
	$('#trial_list').children('li').each(function(idx, item) {
		var elem = $(item);
		
		// good or bad
		var show = (_showGoodTrials == elem.data('good'));
		
		// intervention type
		if (show) {
			var types = elem.data('intervention-types');
			show = active_types.intersects(types);
			
			// count
			for (var i = 0; i < types.length; i++) {
				if (types[i] in per_type) {
					per_type[types[i]]++;
				}
				else {
					per_type[types[i]] = 1;
				}
			}
		}
		
		// trial phase
		if (show) {
			var phases = elem.data('phases');
			if (phases.length > 0) {
				show = active_phases.intersects(phases);
				var has_non_na_phase = false;
				
				// count
				for (var i = 0; i < phases.length; i++) {
					var phase = phases[i];
					if (phase in per_phase) {
						per_phase[phase]++;
					}
					else {
						per_phase[phase] = 1;
					}
					if ('N/A' != phase) {
						has_non_na_phase = true;
					}
				}
				
				if (has_non_na_phase) {
					num_w_phase++;
				}
			}
		}
		
		// apply
		if (show) {
			if (hasMap) {
				_showPinsForTrial(elem.data('trial'), !elem.is(':visible'));
			}
			else {
				_shouldShowPinsForTrials.push(elem.data('trial'));
			}
			// elem.slideDown('fast');
			elem.show();
			num_shown++;
		}
		else {
			// elem.slideUp('fast');
			elem.hide();
		}
	});
	
	// nothing shown? Show hints
	if (0 == num_shown) {
		_showNoTrialsHint();
	}
	else {
		_hideNoTrialsHint();
	}
	
	window.setTimeout(zoomToPins, 100);
	
	// update good/bad selector
	$('#selector_goodbad').children('li').each(function(idx, item) {
		var elem = $(item);
		elem.removeClass('active');
		if (_showGoodTrials == elem.data('is-good')) {
			elem.addClass('active');
		}
	});
	
	// update intervention type selector
	$('#selector_inv_type').children('li').each(function(idx, item) {
		var elem = $(item);
		var type = elem.data('intervention-type');
		
		elem.find('.num_matches').text(type in per_type ? per_type[type] : 0);
	});
	
	// update phase type selector
	if (num_w_phase > 0) {
		$('#selector_inv_phase_parent').show();
		$('#selector_inv_phase').children('li').each(function(idx, item) {
			var elem = $(item);
			var phase = elem.data('phase');
			var num = phase in per_phase ? per_phase[phase] : 0;
			
			if (num > 0) {
				elem.find('.num_matches').text(num);
				elem.show();
			}
			else {
				elem.hide();
			}
		});
	}
	else {
		$('#selector_inv_phase_parent').hide();
	}
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
		stat.hide();
		return;
	}
	
	stat.show().text(status);
}



function _showNoTrialsHint() {
	var hint = $('#no_trials_hint');
	if (!hint.is('*')) {
		hint = $('<h3/>', {'id': 'no_trials_hint'});
	}
	
	// check if at least one study type has been selected
	var has_type = false;
	$('#selector_inv_type').children('li').each(function(idx, item) {
		if ($(item).find('input').prop('checked')) {
			has_type = true;
			return false;
		}
	});
	 
	if (has_type) {
		hint.text("It seems no trials match your criteria");
	}
	else {
		hint.text("Please select at least one study type");
	}
	$('#trials').append(hint);
}

function _hideNoTrialsHint() {
	$('#no_trials_hint').remove();
}


