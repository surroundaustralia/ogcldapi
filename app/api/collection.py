from typing import List

from fastapi import Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from geomet import wkt
import json
from pyldapi.fastapi_framework import Renderer
from rdflib import URIRef, Literal, Graph
from rdflib.namespace import DCTERMS, RDF, DCAT, RDFS

from api.link import *
from api.profiles import *
from config import *
from utils import utils

templates = Jinja2Templates(directory="templates")
g = utils.g


class Collection(object):
    def __init__(
        self,
        uri: str,
        other_links: List[Link] = None,
    ):
        self.uri = uri

        # get graph namespaces to use for prefixes
        self.graph_namespaces = g.query(f"""DESCRIBE <{self.uri}>""").graph

        # sparql query to get props
        non_bnode_query = g.query(
            f"""
            PREFIX dcterms: <http://purl.org/dc/terms/> 
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
            PREFIX geo: <http://www.opengis.net/ont/geosparql#>
            PREFIX ogcldapi: <https://data.surroundaustralia.com/def/ogcldapi/>
            SELECT ?p1 ?p1Label ?o1 ?o1Label ?system_url {{
                <{self.uri}> ?p1 ?o1
                VALUES (?feature ?fc) {{(geo:Feature ogcldapi:FeatureCollection)}}
                OPTIONAL {{?o1 a ?feature ; 
                               dcterms:identifier ?feature_id ;
                               dcterms:isPartOf / dcterms:identifier ?feature_fc_id .
                           BIND(CONCAT("{LANDING_PAGE_URL}/collections/", ?feature_fc_id, "/items/", ?feature_id) AS ?system_url)
                }}
                OPTIONAL {{?o1 a ?fc ;
                               dcterms:identifier ?feature_collection .
                           BIND(CONCAT("{LANDING_PAGE_URL}/collections/", ?feature_collection) AS ?system_url)}}
                OPTIONAL {{ 
                    {{?p1 rdfs:label ?p1Label}} FILTER(lang(?p1Label) = "" || lang(?p1Label) = "en") }}
                OPTIONAL {{ 
                    {{?o1 rdfs:label ?o1Label}} FILTER(lang(?o1Label) = "" || lang(?o1Label) = "en") }}
                FILTER(!ISBLANK(?o1))
                }}"""
        )
        non_bnode_results = [
            {str(k): v for k, v in i.items()} for i in non_bnode_query.bindings
        ]

        # add prefixed URIs (e.g. "skos:prefLabel") to the properties (for display as tooltips in the UI)
        for result_set in [non_bnode_results]:
            for property in result_set:
                for k, v in property.copy().items():
                    if isinstance(v, URIRef):
                        property[f"{k}Prefixed"] = v.n3(
                            self.graph_namespaces.namespace_manager
                        )

        self.properties = [i for i in non_bnode_results]

        # Feature properties
        collection_graph = g.query(f"""DESCRIBE <{self.uri}>""").graph
        self.identifier = collection_graph.value(URIRef(self.uri), DCTERMS.identifier)
        self.title = collection_graph.value(URIRef(self.uri), RDFS.label)
        self.description = collection_graph.value(URIRef(self.uri), DCTERMS.description)

        # for p, o in g.predicate_objects(subject=URIRef(self.uri)):
        #     if p == DCTERMS.title:
        #         self.title = str(o)
        #     elif p == DCTERMS.identifier:
        #         self.identifier = str(o)
        #     elif p == DCTERMS.description:
        #         self.description = markdown.markdown(str(o))

        # Collection other properties
        self.extent_spatial = None
        self.extent_temporal = None
        self.links = [
            Link(
                LANDING_PAGE_URL + "/collections/" + self.identifier + "/items",
                rel=RelType.ITEMS.value,
                type=MediaType.GEOJSON.value,
                title=self.title,
            )
        ]
        if other_links is not None:
            self.links.extend(other_links)

        # self.feature_count = 0
        # for s in g.subjects(predicate=DCTERMS.isPartOf, object=URIRef(self.uri)):
        #     self.feature_count += 1

    def to_dict(self):
        self.links = [x.__dict__ for x in self.links]

        # delattr(self, "feature_count")  # this attribute is for internal use only and can be misleading if communicated
        return self.__dict__

    def to_geo_json_dict(self):
        self.links = [x.__dict__ for x in self.links]

        # delattr(self, "feature_count")  # this attribute is for internal use only and can be misleading if communicated
        return self.__dict__

    def to_geosp_graph(self):
        g = Graph()
        g.bind("geo", GEO)
        g.bind("geox", GEOX)
        g.bind("dcterms", DCTERMS)

        c = URIRef(self.uri)

        g.add((c, RDF.type, DCTERMS.Collection))

        g.add((c, DCTERMS.identifier, Literal(self.identifier)))

        g.add((c, RDFS.label, Literal(self.title)))

        g.add((c, DCTERMS.description, Literal(self.description)))

        return g


class CollectionRenderer(Renderer):
    def __init__(self, request, collection_uri: str, other_links: List[Link] = None):
        self.collection = Collection(collection_uri)
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

        super().__init__(
            request,
            LANDING_PAGE_URL + "/collections/" + self.collection.identifier,
            profiles={
                "oai": profile_openapi,
                "mem": profile_mem
            },
            default_profile_token="oai",
            MEDIATYPE_NAMES=MEDIATYPE_NAMES,
        )

        self.ALLOWED_PARAMS = ["_profile", "_mediatype", "version"]

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
            if self.mediatype == MediaType.JSON.value:
                return self._render_oai_json()
            else:
                return self._render_oai_html()
        elif self.profile == "mem":
            return self._render_mem_html()

    def _render_oai_json(self):
        page_json = {
            "links": [x.__dict__ for x in self.links],
            "collection": self.collection.to_dict(),
        }

        return JSONResponse(
            page_json,
            media_type=str(MediaType.JSON.value),
            headers=self.headers,
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
            DCTERMS.isPartOf,
            DCAT.bbox
        ]

        def add_property(prop: dict, dict: dict, mode: str) -> None:
            """Adds a property to a group dict"""
            object = None
            prop_name = "p1"

            if mode == "prop":
                object = {
                    "value": prop["o1"],
                    "prefix": prop.get("o1Prefixed"),
                    "label": prop.get("o1Label"),
                    "system_url": prop.get("system_url")
                }
            
            if dict.get(prop[prop_name]):  # if prop exists, append child
                if mode == "prop":
                    dict[prop[prop_name]]["objects"].append(object)
                
            else:  # create prop
                dict[prop[prop_name]] = {
                    "uri": prop[prop_name],
                    "prefix": prop.get(f"{prop_name}Prefixed"),
                    "label": prop.get(f"{prop_name}Label"),
                    "objects": [object] if object is not None else None,
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
        for property in self.collection.properties:
            if property["p1"] == RDFS.label or property["p1"] == DCTERMS.description:
                continue
            elif property["p1"] == DCAT.bbox:
                # is dcat:bbox what we should be using for a bounding box? (vs geo:bbox if that's a thing)
                # does bounding box have wkt AND geojson formats? (i.e. asWKT & asGeoJSON)
                # dcat:bbox seems to be only WKT, but the map expects geoJSON
                # locn:geometry is also a bounding box in geoJSON, but unsure if we're using that
                geometry = json.dumps(wkt.loads(property["o1"]))
            matched = False
            for key, value in dicts.items():
                if property["p1"] in value:
                    switch(key, property, "prop")
                    matched = True
                    break
            if not matched:
                switch("other", property, "prop")

        def order_properties(key: str, dict: dict, order_list: List[URIRef]) -> int:
            """Orders the properties of a group dict according to the corresponding order list"""
            if key in order_list:
                return order_list.index(key)
            else:
                return len(dict.keys())

        collection_properties = []
        collection_properties.extend(
            sorted(
                properties.values(),
                key=lambda p: order_properties(p["uri"], properties, properties_order),
            )
        )
        collection_properties.extend(
            sorted(other.values(), key=lambda p: order_properties(p["uri"], other, []))
        )

        _template_context = {
            "uri": self.instance_uri,
            "links": self.links,
            "collection": self.collection,
            "request": self.request,
            "type": sorted(
                type.values(),
                key=lambda p: order_properties(p["uri"], type, type_order),
            ),
            "properties": collection_properties,
            "geometry": geometry,
            "api_title": f"{self.collection.title} - {API_TITLE}",
        }

        return templates.TemplateResponse(
            name="collection.html", context=_template_context, headers=self.headers
        )

    def _render_mem_html(self):
        return RedirectResponse(url=LANDING_PAGE_URL + "/collections/" + self.collection.identifier + "/items")