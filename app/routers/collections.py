from typing import Optional

import fastapi
from fastapi import Request, Response

from rdflib import Literal
from rdflib.namespace import DCTERMS, RDF

from api.collections import CollectionsRenderer
from api.collection import CollectionRenderer
from utils import utils


router = fastapi.APIRouter()
g = utils.g


@router.get("/collections")
def collection(request: Request,
               _view: Optional[str] = None,
               _profile: Optional[str] = None,
               _format: Optional[str] = None,
               _mediatype: Optional[str] = None,
               page: Optional[str] = None,
               per_page: Optional[str] = None,
               limit: Optional[str] = None,
               bbox: Optional[str] = None):
    print("asa")
    return CollectionsRenderer(request).render()


@router.get("/collections/<collection_id>")
# @api.param("collection_id", "The ID of a Collection delivered by this API. See /collections for the list.")
def collection_id(request: Request, collection_id: str = None,
                  _profile: Optional[str] = None,
                  _mediatype: Optional[str] = None):

    # g = get_graph()
    # get the URI for the Collection using the ID
    collection_uri = None
    for s in g.subjects(predicate=DCTERMS.identifier, object=Literal(collection_id)):
        collection_uri = s

    if collection_uri is None:
        return Response(
            "You have entered an unknown Collection ID",
            status_code=400,
            media_type="text/plain"
        )

    return CollectionRenderer(request, collection_uri).render()


# @api.route("/collections/<string:collection_id>/items")
# @api.param("collection_id", "The ID of a Collection delivered by this API. See /collections for the list.")
# class FeaturesRoute(Resource):
#     def get(self, collection_id):
#         return FeaturesRenderer(request, collection_id).render()
#
#
# @api.route("/collections/<string:collection_id>/items/<string:item_id>")
# @api.param("collection_id", "The ID of a Collection delivered by this API. See /collections for the list.")
# @api.param("item_id", "The ID of a Feature in this Collection's list of Items")
# class FeatureRoute(Resource):
#     def get(self, collection_id, item_id):
#         g = get_graph()
#         # get the URI for the Collection using the ID
#         collection_uri = None
#         for s in g.subjects(predicate=DCTERMS.identifier, object=Literal(collection_id)):
#             collection_uri = s
#
#         if collection_uri is None:
#             return Response(
#                 "You have entered an unknown Collection ID",
#                 status=400,
#                 mimetype="text/plain"
#             )
#
#         # get URIs for things with this ID  - IDs may not be unique across Collections
#         for s in g.subjects(predicate=DCTERMS.identifier, object=Literal(item_id)):
#             # if this Feature is in this Collection, return it
#             if (s, DCTERMS.isPartOf, collection_uri) in g:
#                 return FeatureRenderer(request, str(s)).render()
#
#         return Response(
#             "The Feature you have entered the ID for is not part of the Collection you entered the ID for",
#             status=400,
#             mimetype="text/plain"
#         )
