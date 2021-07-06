from typing import Optional

import fastapi
import logging
from fastapi import Request
from utils import utils

from config import *
from rdflib.namespace import RDF, RDFS
from api.conformance import ConformanceRenderer

router = fastapi.APIRouter()
g = utils.g


@router.get(
    "/conformance",
    summary="Conformance Page",
    responses={
        200: {"description": "Conformance page correctly loaded."},
        400: {"description": "Parameter not found or not valid."},
    },
)
def conformance(
    request: Request,
    _view: Optional[str] = None,
    _profile: Optional[str] = None,
    _format: Optional[str] = None,
    _mediatype: Optional[str] = None,
    version: Optional[str] = None,
):
    # q = """
    #     PREFIX dcterms: <http://purl.org/dc/terms/>
    #     PREFIX ogcapi: <https://data.surroundaustralia.com/def/ogcapi/>
    #
    #     SELECT *
    #     WHERE {
    #         ?uri a ogcapi:ConformanceTarget ;
    #            dcterms:title ?title
    #     }
    #     """
    logging.info(f"Conformance page request: {request.path_params}")
    conformance_classes = []
    for s in g.subjects(predicate=RDF.type, object=OGCAPI.ConformanceTarget):
        uri = str(s)
        for o in g.objects(subject=s, predicate=RDFS.label):
            title = str(o)
        conformance_classes.append((uri, title))
    return ConformanceRenderer(request, conformance_classes).render()
