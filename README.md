ClinicalTrials.gov Eligibility
==============================

Extracting and codifying study eligibility criteria from [ClinicalTrials.gov][ct] using [cTakes][].

> This project relies on a private cTAKES module for the time being.


Requirements
------------

### Python

Python 2.7 (probably), with the modules listed in [`requirements.txt`](requirements.txt).

### MongoDB

We're using MongoDB to cache trial data locally.

### SMART Container

If you want to connect to a SMART container, a SMART 0.6+ container is suggested, though there are hacks to support SMART 0.5.


Setup
-----

After initializing the submodules, a symlink to the internally used databases should be functional. If not you must create it:

    $ cd clinical-trials-gov
    $ ln -s ClinicalTrials/databases


### cTakes ###

We checkout cTakes and add the pgpop module. Assuming we are in the main directory:

- Install Maven (This is for OS X, requires [Homebrew][], adapt accordingly)
    
        brew install maven

- Checkout cTakes from the repo  

        svn co https://svn.apache.org/repos/asf/ctakes/trunk ctakes

- Add the pgpop module to ctakes as `ctakes-pgpop` (**THIS IS A PRIVATE MODULE**). Make sure the pom contains the profile `pgpopPreprocessAndSerialize`.

- Add this line to `ctakes/pom.xml` (under the `<modules>` node):  

        <module>ctakes-pgpop</module>

- Create a file named `umls.sh` containing your UMLS username and password:
      
        UMLS_USERNAME='username'
        UMLS_PASSWORD='password'

### MetaMap ###

To evaluate MetaMap, download and install MetaMap:

- Download [from NLM](http://metamap.nlm.nih.gov/#Downloads)
- Extract the archive into our root directory and rename it to `metamap`
- Run the install script:
    
        ./bin/install.sh


### SNOMED CT ###

There is a SNOMED database at _ctakes/ctakes-dictionary-lookup/target/classes/org/apache/ctakes/dictionary/lookup/umls2011ab_ after checking out cTakes, but it's in HSQLDB format which is not easily usable from Python, so we download and use our own copy:

- download [SNOMED CT][snomed]
- from the directory `RF2Release/Full/Terminology` place the following files under the given name into the `databases` directory:
    
    - `sct2_Description_Full-en_INT_xxxxxxx.txt`: `snomed_desc.csv`
    - `sct2_Relationship_Full_INT_xxxxxxxx.txt`: `snomed_rel.csv`
    
    When these files are present, the app will automatically import all SNOMED codes into a local SQLite database, if this has not already been done.


### RxNorm ###

Run the script `ClinicalTrials/databases/rxnorm.sh`, it will guide you through installing RxNorm.


[ct]: http://www.clinicaltrials.gov
[ctakes]: http://ctakes.apache.org
[metamap]: http://metamap.nlm.nih.gov
[homebrew]: http://mxcl.github.com/homebrew/
[snomed]: http://www.nlm.nih.gov/research/umls/licensedcontent/snomedctfiles.html
