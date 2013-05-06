/**
 *  Top level JavaScript defining globals and utility functions.
 */


var _ruleCtrl = null;
var _reportCtrl = null;
var _globals = {};
$(document).ready(function() {
	
	// hide the patient selector if in an iframe
	if (window != window.top) {
		$('#back_to_patient_select').hide();
	}
	
	// load demographics
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
	
	// load problems
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
});


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
		'url': 'trials',
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
		'url': 'trials/' + run_id + '/progress'
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
			console.error(obj1, ' -- ', status, ' -- ', obj2);
			_showTrialStatus('Error, see console');
		}
	});
}

function _getTrialResults(run_id) {
	
}

function _showTrialStatus(status) {
	$('#trials').empty().text(status);
}




/**
 *  Thanks Twitter, like this we can use console.xy without fear.
 */
if ( ! window.console ) {
	(function() {
		var names = ["log", "debug", "info", "warn", "error", "assert", "dir", "dirxml", "group", "groupEnd", "time", "timeEnd", "count", "trace", "profile", "profileEnd"];
		var l = names.length;
		
		window.console = {};
		for (var i = 0; i < l; i++) {
			window.console[names[i]] = function() {};
		}
	}());
}

