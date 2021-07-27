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
    prefix_graph = Graph().parse('static/query_prefixes.ttl', format='turtle')
    # add any dataset specific preferred prefixes from the "preferred-prefixes" graph
    sparql_prefixes = """DESCRIBE * {GRAPH <https://preferred-prefixes> {?s ?p ?o}}"""
    prefix_graph += g.query(sparql_prefixes).graph

    prefixes = {}
    for s, p, o in prefix_graph:
        prefixes[str(o)] = URIRef(s)

    return g, prefixes
