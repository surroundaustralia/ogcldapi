from typing import List
import json
from config import *
from api.link import *
from api.profiles import *
from utils import utils

from geomet import wkt
from fastapi import Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pyldapi import Renderer, RDF_MEDIATYPES

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
        non_bnode_results = [{str(k): v for k, v in i.items()} for i in non_bnode_query.bindings]

        bnode_query = g.query(
            f"""
            PREFIX dcterms: <http://purl.org/dc/terms/> 
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
            SELECT ?p1 ?p1Label ?p2 ?p2Label ?o2 ?o2Label ?o1 {{
                <{self.dataset_uri}> ?p1 ?o1 .
                ?o1 ?p2 ?o2
                OPTIONAL {{ 
                    {{?p1 rdfs:label ?p1Label}} FILTER(lang(?p1Label) = "" || lang(?p1Label) = "en") }}
                OPTIONAL {{
                    {{?p2 rdfs:label ?p2Label}} FILTER(lang(?p2Label) = "" || lang(?p2Label) = "en") }}
                OPTIONAL {{ 
                    {{?o2 rdfs:label ?o2Label}} FILTER(lang(?o2Label) = "" || lang(?o2Label) = "en") }}
                FILTER(ISBLANK(?o1))
                }}"""
        )
        bnode_results = [
            {str(k): v for k, v in i.items()} for i in bnode_query.bindings
        ]

        for result_set in [non_bnode_results, bnode_results]:
            for property in result_set:
                for k, v in property.copy().items():
                    if isinstance(v, URIRef):
                        property[f"{k}Prefixed"] = v.n3(
                            dataset_triples.namespace_manager
                        )
        
        self.properties = [i for i in non_bnode_results]
        self.bnode_properties = [i for i in bnode_results]

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
            "oai"
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
        template_context = {
            "api_title": API_TITLE,
            # "theme": THEME
            "stylesheet": STYLESHEET,
            "header": HEADER,
            "footer": FOOTER
        }
        response = super().render(
            additional_alt_template_context=template_context
        )
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
            if self.mediatype in RDF_MEDIATYPES:
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
        # property dicts
        type = {}
        properties = {}
        other = {}

        # list of property order per group
        type_order = [RDF.type]
        properties_order = [
            DCTERMS.identifier,
            # DCTERMS.isPartOf,
            # DCAT.bbox
        ]

        def add_property(prop: dict, dict: dict, mode: str) -> None:
            """Adds a property to a group dict"""
            object = None
            bnode = None
            geometry = None
            prop_name = "p1"

            if mode == "prop":
                object = {
                    "value": prop["o1"],
                    "prefix": prop.get("o1Prefixed"),
                    "label": prop.get("o1Label"),
                    "system_url": prop.get("system_url")
                }
            elif mode == "bnode":
                bnode = {
                    "pUri": prop["p2"],
                    "pPrefix": prop.get("p2Prefixed"),
                    "pLabel": prop.get("p2Label"),
                    "oValue": prop["o2"],
                    "oPrefix": prop.get("o2Prefixed"),
                    "oLabel": prop.get("o2Label"),
                }
            else:  # geom
                prop_name = "p2"
                geometry = prop["o2"]

            if dict.get(prop[prop_name]):  # if prop exists, append child
                if mode == "prop":
                    dict[prop[prop_name]]["objects"].append(object)
                elif mode == "bnode":
                    bnode_list = dict[prop[prop_name]]["bnodes"].get(prop["o1"])
                    if bnode_list:  # if bnode exists
                        bnode_list.append(bnode)
                    else:
                        dict[prop[prop_name]]["bnodes"][prop["o1"]] = [bnode]
            else:  # create prop
                dict[prop[prop_name]] = {
                    "uri": prop[prop_name],
                    "prefix": prop.get(f"{prop_name}Prefixed"),
                    "label": prop.get(f"{prop_name}Label"),
                    "objects": [object] if object is not None else None,
                    "bnodes": {prop["o1"]: [bnode]} if bnode is not None else None,
                    "geometry": geometry if geometry is not None else None
                }

        # dicts to match keys of order list in switch statement
        dicts = {
            "type_order": type_order,
            "properties_order": properties_order
        }

        # switch statement
        def switch(case: str, prop: dict, mode: str) -> None:
            """Switch statement matching case of which order list the property is in"""
            cases = {
                "type_order": lambda: add_property(prop, type, mode),
                "properties_order": lambda: add_property(prop, properties, mode),
            }
            cases.get(case, lambda: add_property(prop, other, mode))()

        geometry = None

        # properties loop
        for property in self.landing_page.properties:
            if property["p1"] == RDFS.label or property["p1"] == DCTERMS.description:
                continue
            # elif property["p1"] == DCAT.bbox:
            #     geometry = json.dumps(wkt.loads(property["o1"]))
            matched = False
            for key, value in dicts.items():
                if property["p1"] in value:
                    switch(key, property, "prop")
                    matched = True
                    break
            if not matched:
                switch("other", property, "prop")

        # bnode properties loop
        for property in self.landing_page.bnode_properties:
            # omit SpatialMeasure from hasArea
            # if property["p1"] == GEO.hasArea and property["o2"] == GEO.SpatialMeasure:
            #     continue
            if property["p2"] == DCAT.bbox:
                geometry = json.dumps(wkt.loads(property["o2"]))
            matched = False
            for key, value in dicts.items():
                if property["p1"] in value:
                    switch(key, property, "bnode")
                    matched = True
                    break
            if not matched:
                switch("other", property, "bnode")

        def order_properties(key: str, dict: dict, order_list: List[URIRef]) -> int:
            """Orders the properties of a group dict according to the corresponding order list"""
            if key in order_list:
                return order_list.index(key)
            else:
                return len(dict.keys())

        dataset_properties = []
        dataset_properties.extend(
            sorted(
                properties.values(),
                key=lambda p: order_properties(p["uri"], properties, properties_order),
            )
        )
        dataset_properties.extend(
            sorted(other.values(), key=lambda p: order_properties(p["uri"], other, []))
        )

        _template_context = {
            "uri": self.landing_page.uri,
            "title": self.landing_page.title,
            "landing_page": self.landing_page,
            "request": self.request,
            "properties": dataset_properties,
            "type": sorted(
                type.values(),
                key=lambda p: order_properties(p["uri"], type, type_order),
            ),
            "geometry": geometry,
            "api_title": API_TITLE,
            # "theme": THEME,
            "stylesheet": STYLESHEET,
            "header": HEADER,
            "footer": FOOTER
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
        # _template_context = {
        #     "uri": self.dataset.uri,
        #     "label": self.dataset.label,
        #     "description": markdown.markdown(self.dataset.description),
        #     "parts": self.dataset.parts,
        #     "distributions": self.dataset.distributions,
        #     "request": self.request,
        # }

        _template_context = {
            "uri": self.landing_page.uri,
            "title": self.landing_page.title,
            "description": self.landing_page.description,
            "request": self.request,
            "stylesheet": STYLESHEET,
            "header": HEADER,
            "footer": FOOTER
        }

        return templates.TemplateResponse(
            name="dataset.html", context=_template_context, headers=self.headers
        )
