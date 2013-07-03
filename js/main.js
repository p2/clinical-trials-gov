/**
 *  Top level JavaScript defining globals and utility functions.
 */


var _ruleCtrl = null;
var _reportCtrl = null;


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
		var prob_name = $('#' + problem_id).find('div.problem_name').text();
		if (is_manual_problem) {
			prob_name = $('#manual_problem').val();
			$('#manual_submit').text('Cancel');
		}
		if (!prob_name) {
			prob_name = "diabetic cardiomyopathy";
			$('#manual_problem').val(prob_name);
		}
		
		// extract demographics and start searching
		var gender = $('#select_female').is(':checked') ? 'female' : 'male';		// TODO: should we be able to not specify gender?
		var age = 1* $('#demo_age').val();
		
		searchTrials(prob_name, gender, age);
	}
	
	// cleanup and show all problems again
	else {
		cancelTrialSearch();
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
		$('#trial_selectors').empty();
		$('#trials').empty();
		
		clearAllPins();
		hideMap();
		$('#g_map_toggle').hide();
	}
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

Array.prototype.uniqueArray = function() {
	var uniq = {};
	var new_arr = [];
	for (var i = 0, l = this.length; i < l; ++i){
		if (uniq.hasOwnProperty(this[i])) {
			continue;
		}
		new_arr.push(this[i]);
		uniq[this[i]] = 1;
	}
	
	return new_arr;
}

Array.prototype.intersects = function(other) {
	for (var i = 0; i < this.length; i++) {
		for (var j = 0; j < other.length; j++) {
			if (this[i] === other[j]) {
				return true;
			}
		};
	};
	
	return false;
}




/*
 *	-------------
 *	DOM Utilities
 *	-------------
 */
function sortChildren(parent, selector, sortFunc) {
	var items = parent.children(selector).get();
	items.sort(sortFunc);
	
	$.each(items, function(idx, itm) {
		parent.append(itm);
	});
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

