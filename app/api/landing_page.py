from typing import List
from config import *
from api.link import *
from api.profiles import *
from utils import utils

from fastapi import Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pyldapi.fastapi_framework import Renderer

from rdflib import URIRef, Literal, Graph
from rdflib.namespace import DCAT, DCTERMS, RDF, RDFS

import markdown
import logging


templates = Jinja2Templates(directory="templates")
g = utils.g


class LandingPage:
    def __init__(
        self,
        other_links: List[Link] = None,
    ):
        logging.debug("LandingPage()")
        self.uri = LANDING_PAGE_URL
        self.dataset_uri = DATASET_URI
        self.description = None

        dataset_triples = g.query(f"""DESCRIBE <{self.dataset_uri}>""").graph
        self.title = dataset_triples.value(URIRef(self.dataset_uri), RDFS.label)
        self.description = dataset_triples.value(
            URIRef(self.dataset_uri), DCTERMS.description
        )

        non_bnode_query = g.query(
            f"""
            PREFIX dcat: <http://www.w3.org/ns/dcat#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dcterms: <http://purl.org/dc/terms/> 
            SELECT ?p1 ?p1Label ?o1 ?o1Label {{
                <{self.dataset_uri}> ?p1 ?o1 .
                OPTIONAL {{ 
                    {{?p1 rdfs:label ?p1Label}} FILTER(lang(?p1Label) = "" || lang(?p1Label) = "en") }}
                OPTIONAL {{ 
                    {{?o1 rdfs:label ?o1Label}} FILTER(lang(?o1Label) = "" || lang(?o1Label) = "en") }}
                VALUES ?feature {{ dcterms:creator dcterms:created dcterms:publisher dcterms:modified dcat:keyword dcat:theme }}
  				FILTER(?p1=?feature)
                }}"""
        )
        self.properties = [{str(k): v for k, v in i.items()} for i in non_bnode_query.bindings]

        for property in self.properties:
            for k, v in property.copy().items():
                if isinstance(v, URIRef):
                    property[f"{k}Prefixed"] = v.n3(
                        dataset_triples.namespace_manager
                    )

        logging.debug("LandingPage() RDF loops")

        # make links
        self.links = [
            Link(
                LANDING_PAGE_URL,
                rel=RelType.SELF,
                type=MediaType.JSON,
                hreflang=HrefLang.EN,
                title="This document",
            ),
            Link(
                LANDING_PAGE_URL + "/spec",
                rel=RelType.SERVICE_DESC,
                type=MediaType.OPEN_API_3,
                hreflang=HrefLang.EN,
                title="API definition",
            ),
            Link(
                LANDING_PAGE_URL + "/docs",
                rel=RelType.SERVICE_DOC,
                type=MediaType.HTML,
                hreflang=HrefLang.EN,
                title="API documentation",
            ),
            Link(
                LANDING_PAGE_URL + "/conformance",
                rel=RelType.CONFORMANCE,
                type=MediaType.JSON,
                hreflang=HrefLang.EN,
                title="OGC API conformance classes implemented by this server",
            ),
            Link(
                LANDING_PAGE_URL + "/collections",
                rel=RelType.DATA,
                type=MediaType.JSON,
                hreflang=HrefLang.EN,
                title="Information about the feature collections",
            ),
            Link(
                LANDING_PAGE_URL + "/sparql",
                rel=RelType.SPARQL,
                type=MediaType.JSON,
                hreflang=HrefLang.EN,
                title="SPARQL endpoint",
            ),
        ]
        # Others
        if other_links is not None:
            self.links.extend(other_links)
        logging.debug("LandingPage() complete")


class LandingPageRenderer(Renderer):
    def __init__(
        self,
        request,
        other_links: List[Link] = None,
    ):
        logging.debug("LandingPageRenderer()")
        self.landing_page = LandingPage(other_links=other_links)

        super().__init__(
            request,
            self.landing_page.uri,
            {"oai": profile_openapi, "dcat": profile_dcat},
            "oai",
            MEDIATYPE_NAMES=MEDIATYPE_NAMES,
            LOCAL_URIS=LOCAL_URIS,
        )

        # add OGC API Link headers to pyLDAPI Link headers
        self.headers["Link"] = self.headers["Link"] + ", ".join(
            [link.render_as_http_header() for link in self.landing_page.links]
        )

        self.ALLOWED_PARAMS = ["_profile", "_view", "_mediatype", "_format", "version"]

    def render(self):
        logging.debug("LandingPageRenderer.render()")
        for v in self.request.query_params.items():
            if v[0] not in self.ALLOWED_PARAMS:
                return Response(
                    "The parameter {} you supplied is not allowed".format(v[0]),
                    status_code=400,
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
        elif self.profile == "dcat":
            if self.mediatype in Renderer.RDF_SERIALIZER_TYPES_MAP:
                return self._render_dcat_rdf()
            else:
                return self._render_dcat_html()

    def _render_oai_json(self):
        page_json = {}

        links = []
        for link in self.landing_page.links:
            l = {"href": link.href}
            if link.rel is not None:
                l["rel"] = link.rel.value
            if link.type is not None:
                l["type"] = link.type.value
            if link.hreflang is not None:
                l["hreflang"] = link.hreflang.value
            if link.title is not None:
                l["title"] = link.title
            if link.length is not None:
                l["length"] = link.length

            links.append(l)

        page_json["links"] = links

        if self.landing_page.title is not None:
            page_json["title"] = self.landing_page.title

        if self.landing_page.description is not None:
            page_json["description"] = self.landing_page.description

        return JSONResponse(
            page_json, media_type=str(MediaType.JSON.value), headers=self.headers
        )

    def _render_oai_html(self):
        _template_context = {
            "uri": self.landing_page.uri,
            "title": self.landing_page.title,
            "landing_page": self.landing_page,
            "request": self.request,
            "api_title": API_TITLE,
        }

        return templates.TemplateResponse(
            name="landing_page_oai.html",
            context=_template_context,
            headers=self.headers,
        )

    def _render_dcat_rdf(self):
        g = Graph()
        g.bind("dcat", DCAT)
        g.add((URIRef(self.landing_page.uri), RDF.type, DCAT.Dataset))
        g.add(
            (
                URIRef(self.landing_page.uri),
                RDFS.label,
                Literal(self.landing_page.title),
            )
        )
        g.add(
            (
                URIRef(self.landing_page.uri),
                DCTERMS.description,
                Literal(self.landing_page.description),
            )
        )

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return HTMLResponse(
                g.serialize(format="json-ld"), media_type=self.mediatype
            )
        else:
            return Response(
                g.serialize(format=self.mediatype), media_type=self.mediatype
            )

    def _render_dcat_html(self):
        _template_context = {
            "uri": self.dataset.uri,
            "label": self.dataset.label,
            "description": markdown.markdown(self.dataset.description),
            "parts": self.dataset.parts,
            "distributions": self.dataset.distributions,
            "request": self.request,
        }

        return templates.TemplateResponse(
            name="dataset.html", context=_template_context, headers=self.headers
        )
