import logging
import pickle

from config import SPARQL_ENDPOINT, TEST_GRAPH
from rdflib import Graph

g = None
context = Graph().parse('https://raw.githubusercontent.com/surroundaustralia/fsdf-kg/master/edg/ontologies/fsdf.ttl', format='turtle')

def get_graph():
    global g
    global context

    if TEST_GRAPH:
        with open(TEST_GRAPH, 'rb') as handle:
            g = pickle.load(handle)
    else:
        logging.debug("get_graph() for {}".format(SPARQL_ENDPOINT))
        g = Graph("SPARQLStore")
        g.open(SPARQL_ENDPOINT)
    return g
