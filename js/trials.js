/**
 *  Function for trial searching, fetching and listing.
 */

var _trialSearchInterval = null;
var _trialSearchMustStop = false;

var _trialBatchSize = 10;		// 25 might be too much for some computers
var _trialNumExpected = 0;
var _trialNumDone = 0;
var _showGoodTrials = true;
var _trialsPerPage = 50;

var _run_id = null;
var _trial_locations= null;


/**
 *  Entry function to trial search (by term)
 */
function searchTrialsByTerm(prob_term, gender, age, remember_term) {
	_trialSearchMustStop = false;
	_initTrialSearch(prob_term, null, gender, age, remember_term);
}

/**
 *  Alternative seacrh function, searching by medical condition
 */
function searchTrialsByCondition(prob_name, gender, age, remember_cond) {
	_trialSearchMustStop = false;
	_initTrialSearch(null, prob_name, gender, age, remember_cond);
}


function cancelTrialSearch() {
	_trialSearchMustStop = true;
	if (_trialSearchInterval) {
		window.clearInterval(_trialSearchInterval);
		_trialSearchInterval = null;
	}
	
	showTrialStatus();
	resetUI();
}

function resetUI() {
	$('#trial_selectors').find('.trial_selector').empty();
	$('#trial_selectors').find('.trial_opt_selector > ul').empty();
	$('#trial_selectors').hide();
	
	resetShownTrials();
	hideNoTrialsHint();
}

function resetShownTrials() {
	$('#trial_list').empty();
	showNoTrialsHint();
	
	cleanMap();
	geo_hideMap();
	$('#g_map_toggle').hide().find('a').text('Show Map');
}

function cleanMap() {
	_trial_locations = null;
	geo_clearAllPins();
	$('#selected_trial').empty().hide();
}


/**
 *  Kicks off trial search.
 *
 *  "term" takes precedence over "condition", only one is ever being used.
 */
function _initTrialSearch(term, condition, gender, age, remember_input) {
	if (_trialSearchInterval) {
		console.warn('Already searching');
		return;
	}
	
	// reset UI
	resetUI();
	_run_id = null;
	showTrialStatus('Starting...');
	
	// locate the patient first; will just call the callback if no location has been given
	geo_locatePatient($('#demo_location').val(), function(success, lat, lng) {
		var location = success ? (lat + ',' + lng) : null;
		
		// determine term or condition
		var data = {
			'gender': gender,
			'age': age,
			'latlng': location,
			'remember_input': remember_input ? true : false
		};
		var term_or_cond = term ? term : condition;
		data[term ? 'term' : 'cond'] = term_or_cond;
		
		// fire off AJAX call
		$.ajax({
			'url': 'trial_runs',
			'data': data
		})
		.always(function(obj1, status, obj2) {
			if (_trialSearchMustStop) {
				return;
			}
			if ('success' == status) {
				_run_id = obj1;
				if (_trialSearchInterval) {
					window.clearInterval(_trialSearchInterval);
				}
				_trialSearchInterval = window.setInterval(function() { checkTrialStatus(); }, 1000);
			}
			else {
				showTrialStatus('Error searching for trials: ' + obj2);
			}
		});
	});
}


/**
 *  This function is called at an interval, checking server side progress until the server signals "done".
 */
function checkTrialStatus() {
	if (!_run_id) {
		return;
	}
	
	$.ajax({
		'url': 'trial_runs/' + _run_id + '/progress'
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
				
				showTrialStatus('Filtering by demographics...');
				_filterTrialsByDemographics(_run_id);
			}
			
			// an error occurred
			else {
				if (obj1 && obj1.length > 5 && obj1.match(/^error/i)) {
					window.clearInterval(_trialSearchInterval);
					_trialSearchInterval = null;
				}
				
				showTrialStatus(obj1);
			}
		}
		else {
			console.error(obj1, status, obj2);
			showTrialStatus('Error checking trial status: ' + obj2);
			window.clearInterval(_trialSearchInterval);
			_trialSearchInterval = null;
		}
	});
}

function _filterTrialsByDemographics(run_id) {
	loadJSON(
		'trial_runs/' + run_id + '/filter/demographics',
		function(obj1, status, obj2) {
			showTrialStatus('Filtering by problem list...');
			_filterTrialsByProblems(run_id);
		},
		function(obj1, status, obj2) {
			showTrialStatus('Error filtering trials (demographics): ' + obj2);
		}
	);
}

function _filterTrialsByProblems(run_id) {
	loadJSON(
		'trial_runs/' + run_id + '/filter/problems',
		function(obj1, status, obj2) {
			loadTrialOverview(run_id);
		},
		function(obj1, status, obj2) {
			showTrialStatus('Error filtering trials (problems): ' + obj2);
		}
	);
}


function loadTrialOverview(run_id) {
	loadJSON(
		'trial_runs/' + run_id + '/overview',
		function(obj1, status, obj2) {
			if ('intervention_types' in obj1 && 'drug_phases' in obj1) {
				_fillInterventionTypes(obj1['intervention_types']);
				_fillTrialPhases(obj1['drug_phases']);
				
				// show UI
				showTrialStatus();
				showNoTrialsHint();
				$('#trial_selectors').show();
			}
			else {
				console.error('Malformed response:', obj1)
			}
		},
		function(obj1, status, obj2) {
			showTrialStatus('Error retrieving overview data: ' + obj2);
		}
	);
}


function _fillInterventionTypes(num_per_type) {
	if (num_per_type) {
		var opt_type = $('#selector_inv_type');
		var itypes = sortedKeysFromDict(num_per_type);
		
		for (var i = 0; i < itypes.length; i++) {
			var type = itypes[i];
			var elem = _getOptCheckElement(type, 0, false);
			elem.data('intervention-type', type);
			opt_type.append(elem);
			
			// number of trials
			elem.find('.num_matches').text(num_per_type[type]);
		}
		
		// sort types alphabetically
		sortChildren(opt_type, 'li', function(a, b) {
			return $(a).text().toLowerCase().localeCompare($(b).text().toLowerCase());
		});
	}
}

function _fillTrialPhases(num_per_phase) {
	if (num_per_phase) {
		var opt_phase = $('#selector_inv_phase').empty();
		var phases = sortedKeysFromDict(num_per_phase);
		
		for (var i = 0; i < phases.length; i++) {
			var phase = phases[i];
			var elem = _getOptCheckElement(phase, 0, true);
			elem.data('phase', phase);
			opt_phase.append(elem);
			
			// number of trials
			elem.find('.num_matches').text(num_per_phase[phase]);
		}
		
		// sort phases alphabetically
		if (phases.length > 0) {
			sortChildren(opt_phase, 'li', function(a, b) {
				return $(a).text().toLowerCase().localeCompare($(b).text().toLowerCase());
			});
		}
	}
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
		input.prop('checked', true);
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
		input.prop('checked', true);
	}
	
	return elem;
}



function _toggleShowGoodTrials(evt) {
	alert('re-implement me!');
	_showGoodTrials = !_showGoodTrials;
	updateShownHiddenTrials();
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
	
	// update trials
	var from_types = 'selector_inv_type' == elem.parent().attr('id');
	updateShownHiddenTrials(from_types);
}


function _toggleKeyword(elem) {
	alert('not implemented');
	var keyword = $(elem).text();
	var norm = _normalizeKeyword(keyword);
	var for_nct = $(elem).parent().data('trial-nct');
	var offset = $(elem).offset().top;
	var scroll_top = $(window).scrollTop();
	
	// determine if it's already present
	var parent = $('#selector_keywords');
	var present = false;
	var num = 0;
	parent.children('span').each(function(idx) {
		if (norm == $(this).data('normalized')) {
			present = true;
			$(this).remove();
		}
		else {
			num++;
		}
	});
	
	// add keyword
	if (!present) {
		var span = $('<span/>').addClass('tag').addClass('active')
		.data('normalized', norm).text(keyword)
		.click(function(e) {
			_toggleKeyword(this);
		});
		parent.append(span).parent().show();
	}
	else if (0 == num) {
		parent.parent().hide();
	}
	
	// restore scroll position (element has been removed from DOM and replaced!)
	if (offset > 0) {
		offset -= 144;			// TODO: figure out why this is necessary (not correct for 2+ tags)
		
		var new_elem = null;
		$('#trial_list').children().each(function(idx) {
			var trial = $(this).find('.trial').data('trial');
			if (trial && trial.nct == for_nct) {
				new_elem = $(this);
				return false;
			}
		});
		
		if (new_elem) {
			var new_top = new_elem.offset().top - (offset - scroll_top);
			$(window).scrollTop(new_top);
		}
	}
}

function _normalizeKeyword(keyword) {
	return keyword ? keyword.toLowerCase() : null;
}


/**
 *  Loops all trials and shows or hides according to our globals.
 */
function updateShownHiddenTrials(from_types) {
	if (!_run_id) {
		showTrialStatus("I have lost track of our run, please search again");
		return;
	}
	
	// inactivate checkboxes
	showNoTrialsHint('Loading…');
	$('#trial_selectors').find('input[type="checkbox"]').prop('disabled', true);
	
	cleanMap();
	var qry_parts = [];
	
	// get active intervention types
	var active_types = [];
	$('#selector_inv_type').children('li').each(function(idx, item) {
		var elem = $(item);
		if (elem.hasClass('active')) {
			active_types.push(elem.data('intervention-type'));
		}
	});
	if (active_types.length > 0) {
		qry_parts.push('intv=' + active_types.join('|'));
	}
	
	// get active phases
	var all_phases = [];
	var active_phases = [];
	$('#selector_inv_phase').children('li').each(function(idx, item) {
		var elem = $(item);
		all_phases.push(elem);
		if (elem.hasClass('active')) {
			active_phases.push(elem.data('phase'));
		}
	});
	if (active_phases.length > 0) {
		if (active_phases.length < all_phases.length) {		// only pass as param if not all of them are selected
			qry_parts.push('phases=' + active_phases.join('|'));
		}
	}
	
	// no phases selected, check all of them
	else {
		$(all_phases).each(function(idx, elem) {
			elem.find('input').prop('checked', true);
			elem.addClass('active');
		});
	}
	
	// show if we have phases and have selected a type
	if (all_phases.length > 0 && active_types.length > 0) {
		$('#selector_inv_phase_parent').show();
	}
	else {
		$('#selector_inv_phase_parent').hide();
	}
	
	// get active keywords
	var active_keywords = [];
	$('#selector_keywords').children('span').each(function(idx, item) {
		active_keywords.push($(item).data('normalized'));
	});
//	if (active_keywords.length > 0) {
//		qry_parts.push('keywords=' + active_keywords.join('|'));
//	}
	
	// if there is no restriction by type or keyword, show nothing
	if (0 == active_types.length && 0 == active_keywords.length) {
		resetShownTrials();
		$('#trial_selectors').find('input[type="checkbox"]').prop('disabled', false);
		return;
	}
	
	// do we need to reload the numbers per trial phase
	if (from_types) {
		qry_parts.push('reload_phases=1');
		$('#selector_inv_phase').find('.num_matches').text('…');
	}
	var qry = qry_parts.join('&');
	
	// TODO: locally caching all trials (webSQL?) might be neat?
	loadJSON(
		'trial_runs/' + _run_id + '/trials?' + qry,
		function(obj1, status, obj2) {
			hideNoTrialsHint();
			_showTrials(obj1['trials'], 0);
			if ('drug_phases' in obj1) {
				_fillTrialPhases(obj1['drug_phases']);
			}
			$('#trial_selectors').find('input[type="checkbox"]').prop('disabled', false);
			window.setTimeout(geo_zoomToPins, 100);
		},
		function(obj1, status, obj2) {
			showTrialStatus('Error loading trials: ' + obj2);
			hideNoTrialsHint();
			$('#trial_selectors').find('input[type="checkbox"]').prop('disabled', false);
		}
	);
}


/**
 *  Shows the given trials, up to _trialsPerPage, from the given start position.
 */
function _showTrials(trials, start) {
	var trial_list = $('#trial_list');
	if (!start || 0 == start) {
		trial_list.empty();
	}
	$('#show_more_trials').remove();
	$('#g_map_toggle').show();
	
	// no trials to show
	if (!trials || 0 == trials.length || start >= trials.length) {
		if (trials.length > 0 && start >= trials.length) {
			console.warn('Cannot show trials starting at: ', start, 'trials: ', trials);
		}
		
		if (!trials || 0 == trials.length) {
			$('#g_map_toggle > span').text('');
			showNoTrialsHint();
		}
		
		return;
	}
	
	// get active keywords
	var active_keywords = [];
	$('#selector_keywords').children('span').each(function(idx, item) {
		active_keywords.push($(item).data('normalized'));
	});
	
	// calculate range
	var show_max = start + _trialsPerPage;
	if (trials.length > show_max && trials.length < start + _trialsPerPage + (_trialsPerPage / 10)) {
		// if it's less than 10% more, show them all
		show_max = trials.length + start;
	}
	var has_more = false;
	var map = $('#g_map');
	if (!_trial_locations) {
		_trial_locations = [];
	}
	
	for (var i = start; i < trials.length; i++) {
		var trial = new Trial(trials[i]);
		_trial_locations.push.apply(_trial_locations, trial.locationPins());
		
		// add the trial element to the list
		if (i < show_max) {
			var li = $('<li/>').append(can.view('templates/trial_item.ejs', {'trial': trial, 'active_keywords': active_keywords}));
			trial_list.append(li);
			trial.showClosestLocations(g_patient_location, li, 0, 3);
		}
		else {
			has_more = true;
		}
	}
	
	$('#g_map_toggle > span').text(_trial_locations.length > 1000 ? ' (' + _trial_locations.length + ' trial locations)' : '');
	if ($('#g_map').is(':visible')) {
		updateTrialLocations();
	}
	hideNoTrialsHint();
	
	// are there more?
	if (has_more) {
		var more = trials.length - show_max;
		var li = $('<li/>', {'id': 'show_more_trials'}).append('<h1>There are ' + more + ' more trials</h1>');
		var link = $('<a/>', {'href': 'javascript:void(0);'}).text('Show ' + ((_trialsPerPage < more) ? _trialsPerPage + ' more' : 'all'))
		.click(function(e) {
			_showTrials(trials, start + _trialsPerPage);
		});
		
		li.append($('<h1/>').append(link));
		trial_list.append(li);
	}
}



/**
 *  Toggles the trial map
 */
function toggleTrialMap() {
	var map = $('#g_map');
	
	// hide
	if (map.is(':visible')) {
		var link_offset = $('#g_map_toggle').offset().top - $(window).scrollTop();
		geo_hideMap();
		geo_clearAllPins();
		$('#g_map_toggle > a').text('Show Map');
		$('#selected_trial').empty().hide();
		
		// scroll in place
		var new_offset = $('#g_map_toggle').offset().top - $(window).scrollTop();
		if (Math.abs(link_offset - new_offset) > 50) {
			$(window).scrollTop(Math.max(0, $('#g_map_toggle').offset().top - link_offset));
		}
	}
	
	// show
	else {
		geo_showMap();
		// map.append('<div id="g_map_loading">Loading...</div>');
		$('#g_map_toggle > a').text('Hide Map');
		
		// pins
		window.setTimeout(function() {
			updateTrialLocations();
		}, 200);
	}
}

function updateTrialLocations() {
	if (!_trial_locations || 0 == _trial_locations.length) {
		return;
	}
	
	geo_clearAllPins();
	geo_addPins(_trial_locations, false, function(e) {
		showTrialsforPins([this]);
	});
	geo_zoomToPins();
}


/**
 *  May be called with multiple pins (if they are all clustered).
 */
function showTrialsforPins(pins) {
	if (1 == pins.length) {
		geo_highlightPin(pins[0]);
	}
	
	var map_offset = $('#g_map').offset().top - $(window).scrollTop();
	var area = $('#selected_trial').empty().show();
	
	// show all trials corresponding to the pins
	for (var i = 0; i < pins.length; i++) {
		var pin = pins[i];
		
		// TODO: collect active keywords
		var li = $('<li/>').append(can.view('templates/trial_item.ejs', {'trial': pin.trial, 'active_keywords': null}));
		li.append('<a class="dismiss_link" href="javascript:void(0);" onclick="dismissShownTrial(this)">dismiss</a>');
		area.append(li);
		
		// and show the location
		pin.trial.showLocation(li, pin.location);
	}
	
	// scroll the map back
	var new_offset = $('#g_map').offset().top - $(window).scrollTop();
	if (Math.abs(new_offset - map_offset) > 50) {
		$(window).scrollTop(Math.max(200, $('#g_map').offset().top - map_offset));
	}
}

function dismissShownTrial(link) {
	var elem = $(link).closest('li').slideUp('fast', function() {
		$(this).remove();
		
		var area = $('#selected_trial');
		if (0 == area.find('li').length) {
			area.hide();
		}
	});
	geo_unhighlightPin();
}


/**
 *  Display the current trial loading status (or hide it if status is null)
 */
function showTrialStatus(status) {
	var stat = $('#trial_status');
	if (!status) {
		stat.hide();
		return;
	}
	
	stat.show().text(status);
}



function showNoTrialsHint(override_text) {
	var hint = $('#no_trials_hint');
	if (!hint.is('*')) {
		hint = $('<h3/>', {'id': 'no_trials_hint'});
		$('#trials').prepend(hint);
	}
	
	// display arbitrary text? We can do that
	if (override_text && override_text.length > 0) {
		hint.text(override_text);
		return;
	}
	
	// check if at least one study type has been selected
	var has_type = false;
	$('#selector_inv_type').children('li').each(function(idx, item) {
		if ($(item).find('input').prop('checked')) {
			has_type = true;
			return;
		}
	});
	
	// if there is a type, make sure we have selected at least one phase
	if (has_type) {
		var has_phase = false;
		if ($('#selector_inv_phase').is(':visible')) {
			$('#selector_inv_phase').children('li').each(function(idx, item) {
				if ($(item).find('input').prop('checked')) {
					has_phase = true;
					return;
				}
			});
		}
		
		if (!has_phase) {
			hint.text("Please select at least one trial phase");
		}
		else {
			hint.text("It seems no trials match your criteria");
		}
	}
	else {
		hint.text("Please select at least one intervention or observation");
	}
}

function hideNoTrialsHint() {
	$('#no_trials_hint').remove();
}


