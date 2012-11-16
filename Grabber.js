

function Grabber($scope, $http) {
	$scope.raw = null;
	$scope.error_msg = null;
	$scope.running = false;
	$scope.waiting_for = 0;
	$scope.must_stop = false;
	
	$scope.num_all = 0;
	$scope.num_recr = 0;
	$scope.num_curr = 0;
	$scope.num_elig = 0;
	
	// starting and stopping
	$scope.start = function() {
		grabAll();
	}
	
	$scope.stop = function() {
		$scope.must_stop = true;
	}
	
	/**
	 *	Process one single study (from Lilly API)
	 */
	processStudyLilly = function(study) {
		processEligibility(study);
	}
	
	/**
	 *	Process one single study (from ClinicalTrials.gov XML)
	 */
	processStudyCTgov = function(study) {
		if ('url' in study) {
			$scope.waiting_for++;
			grab(study.url + '?displayxml=true', function(data) {
				if ('clinical_study' in data) {
					processEligibility(data.clinical_study);
				}
				$scope.waiting_for--;
			});
		}
	}
	
	/**
	 *	Checks whether the study has eligibility flags set
	 */
	processEligibility = function(res) {
		if ('eligibility' in res && res.eligibility) {
			var elig = res.eligibility;
			
			var min_age = parseInt(elig.minimum_age);
			var max_age = parseInt(elig.maximum_age);
			var has_criteria = ('criteria' in elig && 'textblock' in elig.criteria && elig.criteria.textblock.length > 0 && 'No eligibility criteria' != elig.criteria.textblock);
			
			// we need at least an age boundary or a description
			if (!isNaN(min_age) || !isNaN(max_age) || has_criteria) {
				$scope.num_elig++;
				$scope.raw = elig.criteria.textblock;
				//console.log(elig, elig.criteria.textblock.length);
			}
		}
	}
	
	
	// grab all
	grabAll = function() {
		grab('http://api.lillycoi.com/v1/trials.json?fields=id&limit=1', function(data) {
			$scope.num_all = data.totalCount;
			
			grabRecr();
		});
	}
	
	// grab recruiting
	grabRecr = function() {
		var url = 'http://api.lillycoi.com/v1/trials/search.json?fields=id&query=recr:open&limit=1';		// limit is not respected
		grab(url, function(data) {
			$scope.num_recr = data.totalCount;
			
			grabAndExtractEligible();
		});
	}
	
	// extract those with eligibility data
	grabAndExtractEligible = function() {
		if (grabUntilCurrIter > 0) {
			alert('A previous run is still in progress, wait for it to finish first');
			return;
		}
		
		$scope.num_curr = 0;
		$scope.num_elig = 0;
		$scope.must_stop = false;
		grabUntilCurrIter = 0;
		
		//var url = 'http://api.lillycoi.com/v1/trials.json?fields=id,eligibility&limit=100';
		var url = 'http://clinicaltrials.gov/search?displayxml=true&cond=diabetes&pg=1';
		grabUntil(url, 0,
		
		// process function
		function(data) {
			//var results = data.results;
			var results = data.search_results.clinical_study;
			if (results && results.length > 0) {
				for (var i = 0; i < results.length; i++) {
					$scope.num_curr++;
					
					//processStudyLilly(results[i], $scope);
					processStudyCTgov(results[i], $scope);
				}
			}
		},
		null);
	}
	
	
	grabUntilCurrIter = 0;
	
	// GETs a URL, calls the process_func on the data, looks if there is a next
	// page and if so, calls itself again, until there are no pages left, at
	// which point the success_func is called.
	grabUntil = function(url, max, process_func, success_func) {
		$scope.running = true;
		//$scope.raw = url;
		grab(url, function(data) {
			grabUntilCurrIter++;
			
			// process
			if (process_func) {
				process_func(data);
			}
			
			// next if we're not at max and if we have a next page URI
			//var next = data.nextPageURI;
			var next = url.replace(/pg=\d+/, 'pg=' + (grabUntilCurrIter + 1));
			if ((max < 1 || grabUntilCurrIter < max) && next && !$scope.must_stop) {
				grabUntil(next, max, process_func, success_func);
			}
			
			// all done
			else {
				$scope.running = false;
				$scope.must_stop = false;
				grabUntilCurrIter = 0;
				
				if (success_func) {
					success_func(data);
				}
			}
		});
	}
	
	// generic GET function
	grab = function(url, success_func) {
		$http({
			url: url,
			method: "GET"
		})
		.success(function(data, status, headers, config) {
			if (success_func) {
				if (url.match(/displayxml=true/)) {
					success_func(x2js.xml_str2json(data));
				}
				else {
					success_func(data);
				}
			}
			else {
				console.log('-->', data);
			}
		})
		.error(function(data, status, headers, config) {
			$scope.error_msg = '<b>' + status + '</b>: ' + data;
		});
	}
}

