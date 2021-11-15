import logging
import pickle

from config import SPARQL_ENDPOINT, TEST_GRAPH
from rdflib import Graph, URIRef

g = None
prefixes = None

def get_graph():

    global g
    global prefixes

    if TEST_GRAPH:
        with open(TEST_GRAPH, "rb") as handle:
            g = pickle.load(handle)
    else:
        logging.debug("get_graph() for {}".format(SPARQL_ENDPOINT))
        g = Graph("SPARQLStore")
        g.open(SPARQL_ENDPOINT)

    # get the API set of preferred prefixes (rdfs, skos, owl, geo, etc.)
    static_prefixes = Graph().parse('static/query_prefixes.ttl', format='turtle')
    # add any dataset specific preferred prefixes from the "preferred-prefixes" graph
    sparql_prefixes = """DESCRIBE * {GRAPH <https://preferred-prefixes> {?s ?p ?o}}"""

    try:
        dataset_prefixes = g.query(sparql_prefixes).graph
        static_prefixes += dataset_prefixes
    except Exception as ex:
        logging.info(f"No preferred prefixes found for dataset. {ex}")

    prefixes = {}
    for s, p, o in static_prefixes:
        prefixes[str(o)] = URIRef(s)
        
    return g, prefixes
