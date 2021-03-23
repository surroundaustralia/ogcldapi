import fastapi
from fastapi import Request
from utils.utils import get_graph

from config import *
from rdflib.namespace import DCTERMS, RDF
from api.conformance import ConformanceRenderer

router = fastapi.APIRouter()


@router.get("/conformance")
def conformance(request: Request):
    q = """
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX ogcapi: <https://data.surroundaustralia.com/def/ogcapi/>

        SELECT *
        WHERE {
            ?uri a ogcapi:ConformanceTarget ;
               dcterms:title ?title
        }
        """
    print("ahe")
    graph = get_graph()
    conformance_classes = []
    for s in graph.subjects(predicate=RDF.type, object=OGCAPI.ConformanceTarget):
        uri = str(s)
        for o in graph.objects(subject=s, predicate=DCTERMS.title):
            title = str(o)
        conformance_classes.append((uri, title))
    return ConformanceRenderer(request, conformance_classes).render()
