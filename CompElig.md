Comparing published eligibility criteria to ClinicalTrials.gov
==============================================================

1. search NCT-ids
	http://clinicaltrials.gov/ct2/results?term=atorvastatin&Search=Search
	http://clinicaltrials.gov/ct2/show/NCT00782184?term=atorvastatin&rslt=With&rank=4

2. Find publications with the NCT in the abstract
	http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=(NCT00782184%5BTitle%2FAbstract%5D)
	Extract PMID from <IdList><Id>####</Id></IdList>
	(Docs: http://www.ncbi.nlm.nih.gov/books/NBK25500/)

3. Extract PMCID (we already have PMID)
	http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=20100797&retmode=xml
	Extract from <OtherID Source="NLM">PMC###</OtherId>

4. Find packaged publications via API -- ONLY OPEN ACCESS ARTICLES AVAILABLE
	http://www.pubmedcentral.nih.gov/utils/oa/oa.fcgi?id=PMC3306831
	(Docs: http://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/)
	
	alternative: eutils w/ PMID, but abstract/authors only
	http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=22305462&retmode=xml

5. Download package via API
	ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/83/dd/Lipids_Health_Dis_2012_Jan_31_11_18.tar.gz

6. Open the `.nxml` file to find the article text, the `<sec sec-type="methods">`
   (type might be pipe-separated with other topics, e.g. "materials|methods")
   node should have eligibility criteria
