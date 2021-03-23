import fastapi
from fastapi import Request
from api.collections import CollectionsRenderer
from api.collection import CollectionRender

router = fastapi.APIRouter()


@router.get("/collections")
def collection(request: Request):
    return CollectionsRenderer(request).render()


@router.get("/collections/<string:collection_id>")
@api.param("collection_id", "The ID of a Collection delivered by this API. See /collections for the list.")
def collection_id(self, collection_id):
    g = get_graph()
    # get the URI for the Collection using the ID
    collection_uri = None
    for s in g.subjects(predicate=DCTERMS.identifier, object=Literal(collection_id)):
        collection_uri = s

    if collection_uri is None:
        return Response(
            "You have entered an unknown Collection ID",
            status=400,
            mimetype="text/plain"
        )

    return CollectionRenderer(request, collection_uri).render()
#
#
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
