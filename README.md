ClinicalTrials.gov Eligibility
==============================

Extracting and codifying study eligibility criteria from [ClinicalTrials.gov][ct] using [cTakes][].


Setup
-----


[…]


### cTakes ###

We checkout cTakes and add the pgpop module. Assuming we are in the main directory:

- Install Maven (This is for OS X, requires [Homebrew][], adapt accordingly)
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

- download [SNOMED CT][snomed]
- from the directory `RF2Release/Full/Terminology` place the following files under the given name into the `databases` directory:
    
    - `sct2_Description_Full-en_INT_xxxxxxx.txt`: `snomed_desc.csv`
    - `sct2_Relationship_Full_INT_xxxxxxxx.txt`: `snomed_rel.csv`
    
    When these files are present, the app will automatically import all SNOMED codes into a local SQLite database, if this has not already been done.


[ct]: http://www.clinicaltrials.gov
[ctakes]: http://ctakes.apache.org
[homebrew]: http://mxcl.github.com/homebrew/
[snomed]: http://www.nlm.nih.gov/research/umls/licensedcontent/snomedctfiles.html
