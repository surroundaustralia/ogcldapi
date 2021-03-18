import os
import pickle
from rdflib import Graph

# g = Graph()
# directory = 'D:\Surround\GA\dataset_asgs2016_dggs'
# for filename in os.listdir(directory):
#     if filename.endswith(".ttl"):
#         g.parse(os.path.join(directory, filename))
#         print(len(g))
#         continue
#      else:
#         continue

from rdflib import Graph
from config import SPARQL_ENDPOINT


def get_graph():
    # import logging
    # logging.debug("get_graph() for {}".format(SPARQL_ENDPOINT))
    # print(SPARQL_ENDPOINT)
    # g = Graph("SPARQLStore")
    # g.open(SPARQL_ENDPOINT)

    with open('D:\Surround\GA\dataset_asgs2016_dggs\\default_graph_2.pkl', 'rb') as handle:
        g = pickle.load(handle)
    return g
