ClinicalTrials.gov Eligibility
==============================

Extracting and codifying study eligibility criteria from [ClinicalTrials.gov](http://www.clinicaltrials.gov) using [cTakes](http://incubator.apache.org/ctakes/).


Setup
-----


[…]


### cTakes ###

We checkout cTakes and add the pgpop module. Assuming we are in the main directory:

- Install Maven (This is for OS X, requires [Homebrew](http://mxcl.github.com/homebrew/), adapt accordingly)
  `brew install maven`
- Checkout cTakes from the repo
  `svn co https://svn.apache.org/repos/asf/incubator/ctakes/trunk ctakes`
- add this line to `ctakes/pom.xml` (under the `<modules>` node):
  `<module>ctakes-pgpop</module>`
- `mkdir ctakes_input`
- `mkdir ctakes_output`
- Add the pgpop module to ctakes (currently have it in my Dropbox)
  `cp ~/Dropbox/xy/ctakes-pgpop ctakes/`
- Create a file named `umls.sh` containing your UMLS username and password:
      
      UMLS_USERNAME='username'
      UMLS_PASSWORD='password'


### SNOMED CT ###

There is a SNOMED database at _ctakes/ctakes-dictionary-lookup/target/classes/org/apache/ctakes/dictionary/lookup/umls2011ab_ after checking out cTakes, but it's in HSQLDB format which is not easily usable from Python, so we download and use our own copy:

- download [SNOMED CT](http://download.nlm.nih.gov/umls/kss/IHTSDO20120731/SnomedCT_Release_INT_20120731.zip)

Descriptions are in _SnomedCT_Release_INT_20120731/RF2Release/Full/Terminology/sct2_Description_Full-en_INT_20120731.txt_. Those will automatically be imported into a local SQLite database. If you download a different release, update the path in `run.py` to point to the correct file.
