from typing import List

from fastapi import Response
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pyldapi.fastapi_framework import ContainerRenderer

from api.link import *
from api.profiles import *
from config import *
from utils import utils

templates = Jinja2Templates(directory="templates")
g = utils.g


class Collections:
    def __init__(self):

        collections_query = g.query(
            f"""PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX ogcapi: <https://data.surroundaustralia.com/def/ogcldapi/>
                SELECT ?fc ?identifier ?title ?description
                {{?fc a ogcapi:FeatureCollection ;
                    dcterms:identifier ?identifier ;
                    dcterms:title ?title ;
                    OPTIONAL {{?fc dcterms:description ?description}}
                }} LIMIT {self.per_page} OFFSET {(self.page - 1) * self.per_page}
                """
        )
        collections_query = [
            {str(k): v for k, v in i.items()} for i in collections_query.bindings
        ]
        fc = [str(i["fc"]) for i in collections_query]
        descriptions = [
            i["description"] if "description" in i.keys() else None
            for i in collections_query
        ]
        identifiers = [
            str(i["identifier"]) if "identifier" in i.keys() else None
            for i in collections_query
        ]
        titles = [i["title"] for i in collections_query]
        self.collections = list(zip(fc, identifiers, titles, descriptions))


class CollectionsRenderer(ContainerRenderer):
    def __init__(self, request, other_links: List[Link] = None):
        self.links = [
            Link(
                LANDING_PAGE_URL + "/collections.json",
                rel=RelType.SELF.value,
                type=MediaType.JSON.value,
                title="This Document",
            ),
            Link(
                LANDING_PAGE_URL + "/collections.html",
                rel=RelType.SELF.value,
                type=MediaType.HTML.value,
                title="This Document in HTML",
            ),
        ]
        if other_links is not None:
            self.links.extend(other_links)

        self.page = (
            int(request.query_params.get("page"))
            if request.query_params.get("page") is not None
            else 1
        )
        self.per_page = (
            int(request.query_params.get("per_page"))
            if request.query_params.get("per_page") is not None
            else 20
        )
        # limit
        self.limit = (
            int(request.query_params.get("limit"))
            if request.query_params.get("limit") is not None
            else None
        )

        self.collections = Collections().collections

        self.collections_count = len(self.collections)

        # if limit is set, ignore page & per_page
        if self.limit is not None:
            self.collections = self.collections[0 : self.limit]

        requested_collections = self.collections

        super().__init__(
            request,
            LANDING_PAGE_URL + "/collections",
            "Collections",
            "The Collections of Features delivered by this OGC API instance",
            None,
            None,
            [
                (LANDING_PAGE_URL + "/collections/" + x[1], x[2])
                for x in requested_collections
            ],
            self.collections_count,
            profiles={"oai": profile_openapi},
            default_profile_token="oai",
            MEDIATYPE_NAMES=MEDIATYPE_NAMES,
            LOCAL_URIS=LOCAL_URIS,
        )

        self.ALLOWED_PARAMS = [
            "_profile",
            "_view",
            "_mediatype",
            "_format",
            "page",
            "per_page",
            "limit",
            "bbox",
            "version",
        ]

        # override last_page variable (pyldapi's last_page calculation is incorrect)
        ceiling = lambda a, b: a // b + bool(a % b)
        self.last_page = ceiling(self.collections_count, self.per_page)

    def render(self):
        for v in self.request.query_params.items():
            if v[0] not in self.ALLOWED_PARAMS:
                return Response(
                    "The parameter {} you supplied is not allowed".format(v[0]),
                    status=400,
                )

        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "oai":
            if self.mediatype in [
                "application/json",
                "application/vnd.oai.openapi+json;version=3.0",
                "application/geo+json",
            ]:
                return self._render_oai_json()
            else:
                return self._render_oai_html()

    def _render_oai_json(self):
        collection_dicts = [
            {"uri": x[0], "id": x[1], "title": x[2], "description": x[3]}
            for x in self.collections
        ]

        page_json = {
            "links": [x.__dict__ for x in self.links],
            "collections": collection_dicts,
        }

        return JSONResponse(
            page_json,
            media_type=str(MediaType.JSON.value),
            headers=self.headers,
        )

    def _render_oai_html(self):
        # generate link QSAs from the CollectionsRenderer attributes
        links = {}
        for link_type in ["first_page", "next_page", "prev_page", "last_page"]:
            page = getattr(self, link_type)
            if page:
                links[
                    link_type
                ] = f"{self.instance_uri}?per_page={self.per_page}&page={page}"

        _template_context = {
            "links": self.links,
            "page_links": links,
            "collections": sorted(self.members, key=lambda m: m[1]),
            "request": self.request,
            "pageSize": self.per_page,
            "pageNumber": self.page,
            "api_title": f"Collections - {API_TITLE}",
        }

        return templates.TemplateResponse(
            name="collections_oai.html", context=_template_context, headers=self.headers
        )
