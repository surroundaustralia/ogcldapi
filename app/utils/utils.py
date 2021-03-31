import os
import pickle
from rdflib import Graph
from config import SPARQL_ENDPOINT

g = None


def get_graph():
    # import logging
    # logging.debug("get_graph() for {}".format(SPARQL_ENDPOINT))
    # g = Graph("SPARQLStore")
    # g.open(SPARQL_ENDPOINT)
    global g
    with open('D:\Surround\GA\dataset_asgs2016_dggs\\default_graph_2.pkl', 'rb') as handle:
        g = pickle.load(handle)
    return g
