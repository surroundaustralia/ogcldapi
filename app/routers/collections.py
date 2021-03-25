from typing import Optional

import fastapi
from fastapi import Request, Response

from rdflib import Literal
from rdflib.namespace import DCTERMS, RDF

from api.collections import CollectionsRenderer
from api.collection import CollectionRenderer
from api.features import FeaturesRenderer
from api.feature import FeatureRenderer
from utils import utils


router = fastapi.APIRouter()
g = utils.g


@router.get("/collections",
            summary="Collections Page",
            responses={
                200: {"description": "Collections page correctly loaded."},
                400: {"description": "Parameter not found or not valid."},
            })
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


@router.get("/collections/{collection_id}",
            summary="Collection Id Page",
            responses={
                200: {"description": "Collection Id page correctly loaded."},
                400: {"description": "Parameter not found or not valid."},
            })
def collection_id(request: Request,
                  collection_id: str = None,
                  _profile: Optional[str] = None,
                  _mediatype: Optional[str] = None):

    print("collection_ID")
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


@router.get("/collections/{collection_id}/items",
            summary="Collection Id Items Page",
            responses={
                200: {"description": "Collection Id Items page correctly loaded."},
                400: {"description": "Parameter not found or not valid."},
            })
def collection_id_items(request: Request,
                        collection_id: str = None,
                        _profile: Optional[str] = None,
                        _mediatype: Optional[str] = None):
    print("ITEMS")
    return FeaturesRenderer(request, collection_id).render()


@router.get("/collections/{collection_id}/items/{item_id}",
            summary="Item per Collection Page",
            responses={
                200: {"description": "Item per Collection page correctly loaded."},
                400: {"description": "Parameter not found or not valid."},
            })
def collection_id_items_id(request: Request,
                           collection_id: str = None,
                           item_id: str = None,
                           _profile: Optional[str] = None,
                           _mediatype: Optional[str] = None):

    print("ITEM_ID")
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

    # get URIs for things with this ID  - IDs may not be unique across Collections
    for s in g.subjects(predicate=DCTERMS.identifier, object=Literal(item_id)):
        # if this Feature is in this Collection, return it
        if (s, DCTERMS.isPartOf, collection_uri) in g:
            return FeatureRenderer(request=request,
                                   feature_uri=str(s),
                                   collection_id=collection_id).render()

    return Response(
        "The Feature you have entered the ID for is not part of the Collection you entered the ID for",
        status_code=400,
        media_type="text/plain"
    )