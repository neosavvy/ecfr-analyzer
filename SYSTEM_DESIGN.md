Analyzer
1. For each agency request Search Results - Documents and then store those documents in a database
2. For each document compute the latest version's metrics, and then walk backwards through the history of that document and compute metrics until we hit the first version

The Metrics are:
- Word Count
- Sentence Count
- Paragraph Count
- Section Count
- Subpart Count
- Authors Total (Number of unique authors who have touched the document)
- Revision Authors (Number of authors who touched the document in this revision)
- Can we score a document revision for overall understanability or complexity
- Simplicity Score


The way I want the analyzer to work is:
1. Create an API that has a few functions on it
    1. Find all agencies and store them in a database, return all agencies as a list
    2. Retrieve all documents for a given agency and store them in a database
    3. Process documents for agency



The way it works for real:

1. Fetch Agencies
2. Search Titles base on the following with agency slug
curl -X GET "https://www.ecfr.gov/api/search/v1/results?agency_slugs%5B%5D=agency-for-international-development&per_page=20&page=1&order=relevance&paginate_by=results" -H "accept: application/json"
3. Search each search result in the following using paramters 
curl -X GET "https://www.ecfr.gov/api/versioner/v1/full/2016-12-16/title-48.xml?chapter=7&appendix=\"Appendix I to Chapter 7\"" -H "accept: application/xml"