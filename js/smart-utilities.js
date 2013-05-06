/**
 *  SMART Utilities
 */


/**
 *  Sorts medication objects based on their med['sp:drugName']['dcterms:title'] attribute, ascending.
 */
function compareMedByNameASC(a, b) {
	if (!('sp:drugName' in a)) {
		return 1;
	}
	if (!('dcterms:title' in a['sp:drugName'])) {
		return 1;
	}
	if (!('sp:drugName' in b)) {
		return -1;
	}
	if (!('dcterms:title' in b['sp:drugName'])) {
		return -1;
	}
	
	if (a['sp:drugName']['dcterms:title'] < b['sp:drugName']['dcterms:title']) {
		return -1;
	}
	if (a['sp:drugName']['dcterms:title'] > b['sp:drugName']['dcterms:title']) {
		return 1;
	}
	return 0;
}

/**
 *  Sorts problem objects based on their prob['sp:drugName']['dcterms:title'] attribute, ascending.
 */
function compareProblemByNameASC(a, b) {
	if (!('sp:problemName' in a)) {
		return 1;
	}
	if (!('dcterms:title' in a['sp:problemName'])) {
		return 1;
	}
	if (!('sp:problemName' in b)) {
		return -1;
	}
	if (!('dcterms:title' in b['sp:problemName'])) {
		return -1;
	}
	
	if (a['sp:problemName']['dcterms:title'] < b['sp:problemName']['dcterms:title']) {
		return -1;
	}
	if (a['sp:problemName']['dcterms:title'] > b['sp:problemName']['dcterms:title']) {
		return 1;
	}
	return 0;
}

/**
 *  Sorts objects based on their "date" attribute, descending.
 */
function compareByDateDESC(a, b) {
	if (!('date' in a)) {
		return 1;
	}
	if (!('date' in b)) {
		return -1;
	}
	
	if (parseInt(a.date) < parseInt(b.date)) {
		return 1;
	}
	if (parseInt(a.date) > parseInt(b.date)) {
		return -1;
	}
	return 0;
}
