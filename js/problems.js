/**
 *  Functions for problem handling
 */


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
			$('#patient_problems').html('templates/patient_problems.ejs', {'data': json, 'last_manual_condition': _last_manual_condition});
		}
		else {
			$('#patient_problems').text('Could not load the problem list, see the console for details');
			console.warn('No good response for problems', obj1, obj2);
		}
	});
}


/**
 *  Routes to the correct trial-search-start or -stop function
 */
function didClickProblem(problem_id, is_reload) {
	var prob_elem = $('#' + problem_id);
	if (!$('#' + problem_id).is('*')) {
		alert('Error, see Browser console');
		console.error('didClickProblem("' + problem_id + '") -- no such problem_id');
		return;
	}
	
	// start or stop searching for trials
	if (is_reload || !prob_elem.hasClass('active')) {
		hideProblemsAndStartTrialSearch(problem_id);
	}
	else {
		cancelTrialSearchAndShowProblemList(problem_id);
	}
}


/**
 *  Collapses all problems except the chosen one and initiates trial search
 */
function hideProblemsAndStartTrialSearch(problem_id) {
	var is_manual_problem = ('prob_manual' == problem_id);
	var prob_name = $('#' + problem_id).find('div.problem_name').text();
	if (is_manual_problem) {
		prob_name = $('#manual_problem').val();
	}
	
	if (!prob_name) {
		$('#manual_problem').focus();
		return;
	}
	
	var prob_elem = $('#' + problem_id);
	prob_elem.addClass('active');
	
	// hide other problems
	$('#problem_list').find('li').each(function(idx, elem) {
		if (problem_id != elem.getAttribute('id')) {
			$(elem).slideUp('fast');
		}
	});
	
	// add refresh and cancel buttons
	if (!is_manual_problem) {
		var canc = $('#cancel_trials');
		if (!canc.is('*')) {
			canc = $('<button/>', {'type': 'button', 'id': 'cancel_trials'}).text("Cancel");
		}
		prob_elem.prepend(canc);
	}
	else {
		$('#manual_cancel').show();
		$('#manual_submit').hide();
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
	
	// extract demographics and start searching
	var gender = $('#select_female').is(':checked') ? 'female' : 'male';		// TODO: should we be able to not specify gender?
	var age = 1* $('#demo_age').val();
	
	searchTrials(prob_name, gender, age, ('prob_manual' == problem_id));
}


/**
 *  Aborts trial search and reverts UI to show the problem list again
 */
function cancelTrialSearchAndShowProblemList(problem_id) {
	cancelTrialSearch();
	
	// show all problems again
	$('#problem_list').find('li').each(function(idx, elem) {
		$(elem).slideDown('fast');
	});
	
	// reset UI
	$('#refresh_trials').remove();
	$('#cancel_trials').remove();
	$('#manual_cancel').hide();
	$('#manual_submit').show();
	
	if (problem_id) {
		$('#' + problem_id).removeClass('active');
	}
	
	$('#selected_trial').empty();
	$('#trial_selectors').empty();
	$('#trials').empty();
	
	clearAllPins();
	hideMap();
	$('#g_map_toggle').hide();
}
