/**
 *  Top level JavaScript defining globals and utility functions.
 */


var _ruleCtrl = null;
var _reportCtrl = null;
var _globals = {};


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
function didClickProblem(problem_id) {
	var prob_list = $('#problem_list');
	var prob_elem = $('#' + problem_id);
	if (!prob_elem.is('*')) {
		alert('Error');
		return;
	}
	
	// problem selected, hide all other and search for trials
	if (!prob_elem.hasClass('active')) {
		prob_elem.addClass('active');
		$('#select_prompt').text("Showing trials pertaining to:");
		
		prob_list.find('li').each(function(idx, elem) {
			if (problem_id != elem.getAttribute('id')) {
				$(elem).slideUp('fast');
			}
		});
		
		// search by problem name
		var prob_name = $('#' + problem_id).find('div.bigger').text();
		if (!prob_name) {
			prob_name = "diabetic cardiomyopathy";
		}
		
		_initTrialSearch(prob_name);
	}
	
	// show all problems again
	else {
		prob_list.find('li').each(function(idx, elem) {
			$(elem).slideDown('fast');
		});
		
		prob_elem.removeClass('active');
		$('#select_prompt').text("Choose for which problem to find trials:");
		$('#trials').empty();
	}
}


var _trialSearchInterval = null;

function _initTrialSearch(problem_name) {
	if (_trialSearchInterval) {
		console.warn('Already searching');
		return;
	}
	
	_showTrialStatus('Starting...');
	
	$.ajax({
		'url': 'trial_runs',
		'data': {'cond': problem_name}
	})
	.always(function(obj1, status, obj2) {
		if ('success' == status) {
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
			else {
				
				// an error occurred
				if (obj1 && obj1.length > 5 && obj1.match(/^error/i)) {
					window.clearInterval(_trialSearchInterval);
					_trialSearchInterval = null;
				}
				
				// show status
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
			_showTrialStatus();
			_loadTrials(obj1);
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
	var list_good = $('<ul/>', {'id': 'trials_good'});
	var list_bad = $('<ul/>', {'id': 'trials_bad'});
	
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
				
				// got a trial, show in appropriate list
				if (this.reason) {
					obj1.reason = this.reason;
					list_bad.append('templates/trial_list.ejs', {'trial': obj1});
				}
				else {
					list_good.append('templates/trial_list.ejs', {'trial': obj1});
				}
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

