Instructions
============

The [_Trial Eligibility_](/) app is designed to find clinical trials relevant for a specific patient.

Quickstart
----------

Set the patient's gender to “female”, age to “54” and location to “Boston, MA”. We will search for trials that specify to study “arthritis” and “Anti-TNF”, so enter “arthritis, anti-tnf” into the seach box. Click “Go”.

The resulting trials (60 at this time) are then divided into “Potential trials” (59 at this time) and “Ineligible trials” (1 trial studying juvenile idiopathic arthritis at this time).

Assuming we are interested in drug trials we check the “Drug” checkbox. This will show all drug trials (33 at this time), ordered by distance, starting with locations closest to Boston. The results can be further reduced by limiting the drug trials to only the desired trial phases by unchecking the appropriate boxes to the right under “Trial Phase”.

You may also click “Show map” to display a map of all trial locations. As there are over 1,000 locations this may take a few seconds to load, depending on your computer.

Patient Demographics
--------------------
Upon launching the app the user has the ability to set his patient's gender, age and location. The latter two are optional but will enhance search results:

* Gender: trials that only accept patients of the opposite gender will be filtered
* Age: trials that exclude patients of the given age will be filtered
* Location: trials will be ordered by the trial recruitment center closest to the patient

Trial Search
------------

The search box can take multiple arguments and will forward to ClinicalTrials.gov with a few substitutions. Keywords “AND” and “OR” can be used, the former will also be used when arguments are separated by comma. Only trials that have specified to be (or will be) actively recruiting will be returned.

Trial Results
-------------

If trials were filtered, e.g. by gender or age, a switch to toggle between unfiltered (“potential trials”) and filtered (“ineligible trials”) will be presented and allows to review trials that were automatically filtered.

### Intervention/Observation

The next step is to select the desired study type from a list of  available intervention types and an “observational” option, if observational studies were returned. Upon selection, trials of the desired type will be shown. Multiple study types can be chosen.

### Trial Phase

If trials of the chosen type(s) specify trial phases, the available phases will appear to the right of the “Intervention/Observation” selector. All phases are active by default and may be used to reduce the number of results by only checking the desired trial phases.

### Map

Trial recruitment locations can be shown on a map by clicking the “Show Map” link. Locations are clustered based on the zoom level, clicking on clusters zooms in to the respective area. Individual pins can be clicked and the trials being conducted at that location will be shown above the map.

> Note that if there are over a thousand locations to be shown the number of locations will be indicated to the right of the “Show Map” link in red and the map may load slowly.

### Trials

Trials matching the chosen criteria will be ordered by closest trial center, if the patient's location was entered, unordered otherwise. Each trial displays its title, the phase if applicable, its NCT-number as a link to ClinicalTrials.gov and a link to show/hide the eligibility criteria on the left.

On the right side the address of the closest 3 locations are shown, with a link to incrementally reveal more locations. Clicking the “contact” link shows the trial center's contact information, which may be specific to the trial location or may be the trial's overall contact.

