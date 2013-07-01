/**
 *  Top level JavaScript defining globals and utility functions.
 */


var _ruleCtrl = null;
var _reportCtrl = null;
var _patient_loc = null;


/**
 *  Called when the DOM is ready, this function starts loading patient data.
 */
function initApp() {
	// hide the patient selector if in an iframe
	if (window != window.top) {
		$('#back_to_patient_select').hide();
	}
	
	// load patient data
	loadDemographics();
	loadProblemList();
}


/**
 *  Load patient demographics.
 */
function loadDemographics() {
	$.ajax({
		'url': 'demographics',
		'dataType': 'json'
	})
	.always(function(obj1, status, obj2) {
		var json = ('success' == status) ? obj1 : (('parsererror' == status) ? {} : null);		// empty JSON generates "parsererror"
		var demo = {};
		if (json) {
			demo = json;
		}
		else {
			console.warn('No good response for demographics', obj1, obj2);
		}
		
		// display demographics
		$('#patient_overview').html('templates/patient_demographics.ejs', {'demo': demo});
	});
}

/**
 *  Load problem list.
 */
function loadProblemList() {
	$.ajax({
		'url': 'problems',
		'dataType': 'json'
	})
	.always(function(obj1, status, obj2) {
		var json = ('success' == status) ? obj1 : (('parsererror' == status) ? {} : null);		// empty JSON generates "parsererror"
		
		// display problem list
		if (json) {
			$('#patient_problems').html('templates/patient_problems.ejs', {'data': json});
		}
		else {
			$('#patient_problems').text('Could not load the problem list, see the console for details');
			console.warn('No good response for problems', obj1, obj2);
		}
	});
}


/**
 *  Functions for testing purposes.
 */
function didClickProblem(problem_id, is_reload) {
	var prob_list = $('#problem_list');
	var prob_elem = $('#' + problem_id);
	if (!prob_elem.is('*')) {
		alert('Error');
		return;
	}
	
	// problem selected, hide all other and search for trials
	if (is_reload || !prob_elem.hasClass('active')) {
		var is_manual_problem = ('prob_manual' == problem_id);
		prob_elem.addClass('active');
		
		// hide other problems
		prob_list.find('li').each(function(idx, elem) {
			if (problem_id != elem.getAttribute('id')) {
				$(elem).slideUp('fast');
			}
		});
		
		// add refresh and cancel buttons
		if (!is_manual_problem) {
			var canc = $('#cancel_trials');
			if (!canc.is('*')) {
				canc = $('<button/>', {'type': 'clear', 'id': 'cancel_trials'}).text("Cancel");
			}
			prob_elem.prepend(canc);
		}
		
		var refr = $('#refresh_trials');
		if (!refr.is('*')) {
			refr = $('<button/>', {'type': 'button', 'id': 'refresh_trials'}).text("Refresh");
		}
		refr.click(function(e) {
			didClickProblem(problem_id, true);
			e.stopPropagation();
		});
		prob_elem.prepend(refr);
		
		// search by problem name
		var prob_name = $('#' + problem_id).find('div.bigger').text();
		if (is_manual_problem) {
			prob_name = $('#manual_problem').val();
			$('#manual_submit').text('Cancel');
		}
		if (!prob_name) {
			prob_name = "diabetic cardiomyopathy";
			$('#manual_problem').val(prob_name);
		}
		
		// extract demographics
		var gender = $('#select_female').is(':checked') ? 'female' : 'male';		// TODO: should we be able to not specify gender?
		var age = 1* $('#demo_age').val();
		
		_initTrialSearch(prob_name, gender, age);
	}
	
	// cleanup and show all problems again
	else {
		prob_list.find('li').each(function(idx, elem) {
			$(elem).slideDown('fast');
		});
		
		// reset manual field
		if ('prob_manual' == problem_id) {
			$('#manual_problem').val('');
			$('#manual_submit').text('Go');
		}
		
		// reset UI
		$('#refresh_trials').remove();
		$('#cancel_trials').remove();
		prob_elem.removeClass('active');
		$('#selected_trial').empty();
		$('#trials').empty();
		clearAllPins();
		hideMap();
	}
}


var _trialSearchInterval = null;

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
			locatePatient(function(success, location) {
				if (success) {
					_patient_loc = location;
				}
				else {
					console.warn("Failed to locate the patient");
					_patient_loc = null;
				}
				
				// load the trials
				_loadTrials(obj1);
			});
		}
		else {
			console.error(obj1, status, obj2);
			_showTrialStatus('Error filtering trials (problems), see console');
		}
	});
}

function _loadTrials(trial_tuples) {
	var main = $('#trials');
	var loader = $('<div/>', {'id': 'trial_loader'}).text('Loading trials...');
	main.append(loader);
	
	var num_good = 0;
	var num_bad = 0;
	var list_good = $('<ul/>', {'id': 'trials_good'}).addClass('trial_list');
	var list_bad = $('<ul/>', {'id': 'trials_bad'}).addClass('trial_list');
	
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
				if (loader) {
					loader.remove();
					loader = null;
				}
				
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
					
					// get closest centre
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
								
				// show in appropriate list
				obj1.reason = this.reason;
				var li = $('<li/>').html('templates/trial_item.ejs', {'trial': obj1});
				li.data('distance', obj1.closest);
				
				var my_list = this.reason ? list_bad : list_good;
				my_list.append(li);
				
				// sort continuously
				var li_items = my_list.children('li').get();
				li_items.sort(function(a, b) {
					return $(a).data('distance') - $(b).data('distance');
				});
				$.each(li_items, function(idx, itm) { my_list.append(itm); });
			}
			else {
				console.error(obj1, status, obj2);
			}
		});
	}
	
	// add to DOM
	var head_good = $('<h3/>').text('Potential Trials (' + num_good + ' of ' + trial_tuples.length + ')');
	var head_bad = $('<h3/>').text('Ineligible Trials (' + num_bad + ' of ' + trial_tuples.length + ')');
	main.append(head_good);
	main.append(list_good);
	main.append(head_bad);
	main.append(list_bad);
}

function _showTrialStatus(status) {
	$('#trials').empty().text(status);
}




/*
 *  ----------------------------
 *  Extending Array capabilities
 *  ----------------------------
 */

Array.prototype.contains = function(obj) {
	return (this.indexOf(obj) >= 0);
}

Array.prototype.indexOf = function(obj) {
	for(var i = 0; i < this.length; i++) {
		if (this[i] == obj)
			return i;
	}
	
	return -1;
}


/*
 *	-----------------
 *	Text manipulation
 *	-----------------
 */

function text2html(string) {
	if (!string)
		return '';
	
	var conv = string.replace(/(^\s+)|(\s+$)/g, '');			// replace leading/trailing whitespace
	conv = conv.replace(/(\r\n|\n)/g, "<br />");				// replace \n with <br />
	
	return conv;
}


/**
 *  Thanks Twitter, with this we can use console.xy without fear.
 */
if (!window.console) {
	(function() {
		var names = ["log", "debug", "info", "warn", "error", "assert", "dir", "dirxml", "group", "groupEnd", "time", "timeEnd", "count", "trace", "profile", "profileEnd"];
		var l = names.length;
		
		window.console = {};
		for (var i = 0; i < l; i++) {
			window.console[names[i]] = function() {};
		}
	}());
}

