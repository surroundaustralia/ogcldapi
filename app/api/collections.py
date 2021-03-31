from pyldapi import ContainerRenderer
from typing import List

from api.link import *
from api.profiles import *
from utils import utils

from config import *
from fastapi import Response
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from rdflib import URIRef
from rdflib.namespace import DCTERMS, RDF

templates = Jinja2Templates(directory="templates")
g = utils.g


class Collections:
    def __init__(self):
        self.collections = []
        for s in g.subjects(predicate=RDF.type, object=OGCAPI.Collection):
            if (s, DCTERMS.isPartOf, URIRef(DATASET_URI)) in g:
                identifier = None
                title = None
                description = None
                for p, o in g.predicate_objects(subject=s):
                    if p == DCTERMS.identifier:
                        identifier = str(o)
                    elif p == DCTERMS.title:
                        title = str(o)
                    elif p == DCTERMS.description:
                        description = str(o)

                self.collections.append((str(s), identifier, title, description))


class CollectionsRenderer(ContainerRenderer):
    def __init__(self, request, other_links: List[Link] = None):
        self.links = [
            Link(
                LANDING_PAGE_URL + "/collections.json",
                rel=RelType.SELF.value,
                type=MediaType.JSON.value,
                title="This Document"
            ),
            Link(
                LANDING_PAGE_URL + "/collections.html",
                rel=RelType.SELF.value,
                type=MediaType.HTML.value,
                title="This Document in HTML"
            ),
        ]
        if other_links is not None:
            self.links.extend(other_links)

        self.page = (
            int(request.query_params.get("page")) if request.query_params.get("page") is not None else 1
        )
        self.per_page = (
            int(request.query_params.get("per_page"))
            if request.query_params.get("per_page") is not None
            else 20
        )
        # limit
        self.limit = int(request.query_params.get("limit")) if request.query_params.get("limit") is not None else None

        self.collections = Collections().collections

        print("Collections", self.collections)
        self.collections_count = len(self.collections)

        print("len collections count", self.collections_count)
        print("limit", self.limit)
        # if limit is set, ignore page & per_page
        if self.limit is not None:
            self.collections = self.collections[0:self.limit]

        requested_collections = self.collections

        super().__init__(
            request,
            LANDING_PAGE_URL + "/collections",
            "Collections",
            "The Collections of Features delivered by this OGC API instance",
            None,
            None,
            [(LANDING_PAGE_URL + "/collections/" + x[1], x[2]) for x in requested_collections],
            self.collections_count,
            profiles={"oai": profile_openapi},
            default_profile_token="oai",
            MEDIATYPE_NAMES=MEDIATYPE_NAMES,
            LOCAL_URIS=LOCAL_URIS
        )

        self.ALLOWED_PARAMS = ["_profile",
                               "_view",
                               "_mediatype",
                               "_format",
                               "page",
                               "per_page",
                               "limit",
                               "bbox",
                               "version"]

    def render(self):
        for v in self.request.query_params.items():
            if v[0] not in self.ALLOWED_PARAMS:
                return Response("The parameter {} you supplied is not allowed".format(v[0]), status=400)

        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "oai":
            if self.mediatype in ["application/json", "application/vnd.oai.openapi+json;version=3.0", "application/geo+json"]:
                return self._render_oai_json()
            else:
                return self._render_oai_html()

    def _render_oai_json(self):
        collection_dicts = [
            {
                "uri": x[0],
                "id": x[1],
                "title": x[2],
                "description": x[3]
            } for x in self.collections
        ]

        page_json = {
            "links": [x.__dict__ for x in self.links],
            "collections": collection_dicts
        }

        return JSONResponse(
            page_json,
            media_type=str(MediaType.JSON.value),
            headers=self.headers,
        )

    def _render_oai_html(self):
        # pagination = Pagination(page=self.page, per_page=self.per_page, total=self.collections_count)
        # paginate
        # print("paginate", paginate(self.members))
        # print(self.members)
        # pag(self.members)
        print(self.per_page)
        print(self.page)
        _template_context = {
            "links": self.links,
            "collections": self.members,
            "request": self.request,
            "pageSize": self.per_page,
            "pageNumber": self.page
        }

        return templates.TemplateResponse(name="collections_oai.html",
                                          context=_template_context,
                                          headers=self.headers)
