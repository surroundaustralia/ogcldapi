# Description
tbc  
A conversion of the ogc-ld-api repository (https://bitbucket.org/surroundbitbucket/ogc-api-ld/src/master/) from flask to fastapi from scratch.

# Instructions
To run an api locally, set the following Environment Variables.  
SPARQL_ENDPOINT: The SPARQL endpoint containing a dataset (and feature collections) which the API will serve.  
DATASET_URI: The URI of the dataset in the triplestore. The API will look for this dataset, then 'crawl' the data to look for feature collections within it, and features within these etc.
LANDING_PAGE: The URI for the front page of the API. If running locally, this will be http://localhost:9000 (unless you've changed the port). If hosting on the web, use the domain name the API is hosted at.

## Currently we are hosting a number of datasets, so the following will work when running the API locally (it will present data hosted in our triplestore on AWS):
SPARQL_ENDPOINT=http://fuseki.surroundaustralia.com/placenames  
DATASET_URI=https://linked.data.gov.au/dataset/placenames 
LANDING_PAGE_URL=http://localhost:9000   
Also:  
SPARQL_ENDPOINT=http://fuseki.surroundaustralia.com/floods  
DATASET_URI=https://linked.data.gov.au/dataset/floods 
LANDING_PAGE_URL=http://localhost:9000   