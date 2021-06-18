from enum import Enum
from typing import ChainMap
from typing import List

from fastapi import Response
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from geojson_rewind import rewind
from geomet import wkt
from pyldapi.fastapi_framework import Renderer
from rdflib import Graph
from rdflib import URIRef, Literal, BNode
from rdflib.namespace import DCTERMS, RDF, RDFS

from api.link import *
from api.profiles import *
from config import *
from utils import utils

templates = Jinja2Templates(directory="templates")
g = utils.g
geo_context = utils.context

class GeometryRole(Enum):
    Boundary = "https://linked.data.gov.au/def/geometry-roles/boundary"
    BoundingBox = "https://linked.data.gov.au/def/geometry-roles/bounding-box"
    BoundingCircle = "https://linked.data.gov.au/def/geometry-roles/bounding-circle"
    Concave = "https://linked.data.gov.au/def/geometry-roles/concave-hull"
    Convex = "https://linked.data.gov.au/def/geometry-roles/convex-hull"
    Centroid = "https://linked.data.gov.au/def/geometry-roles/centroid"
    Detailed = "https://linked.data.gov.au/def/geometry-roles/detailed"


class CRS(Enum):
    WGS84 = "http://www.opengis.net/def/crs/EPSG/0/4326"  # "http://epsg.io/4326"
    TB16PIX = "https://w3id.org/dggs/tb16pix"


class Geometry(object):
    def __init__(self, coordinates: str, role: GeometryRole, label: str, crs: CRS):
        self.coordinates = coordinates
        self.role = role
        self.label = label
        self.crs = crs

    def to_dict(self):
        return {
            "coordinates": self.coordinates,
            "role": self.role.value,
            "label": self.label,
            "crs": self.crs.value,
        }

    def to_geo_json_dict(self):
        # this only works for WGS84 coordinates, no differentiation on role for now
        if self.crs == CRS.WGS84:
            return wkt.loads(self.coordinates)
        else:
            return TypeError("Only WGS84 geometries can be serialised in GeoJSON")


class Feature(object):
    def __init__(
            self,
            uri: str,
            other_links: List[Link] = None):
        self.uri = uri
        self.geometries = []

        # get graph namespaces + geosparql namespaces as we want their prefixes for display
        graph_namespaces = g.query(f"""DESCRIBE <{self.uri}>""").graph
        graph_namespaces += geo_context

        non_bnode_query = g.query(f"""
            PREFIX dcterms: <http://purl.org/dc/terms/> 
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
            SELECT ?pred ?predLabel ?obj ?objLabel {{
                <{self.uri}> ?pred ?obj 
                OPTIONAL {{ 
                    {{?pred rdfs:label ?predLabel}} UNION {{?pred skos:prefLabel ?predLabel}} UNION {{?pred dcterms:title ?predLabel}} }}
                OPTIONAL {{ 
                    {{?obj rdfs:label ?objLabel}} UNION {{?obj skos:prefLabel ?objLabel}} UNION {{?obj dcterms:title ?objLabel}} }}
                FILTER(!ISBLANK(?obj))
                }}""")
        non_bnode_results = [{str(k): v for k, v in i.items()} for i in non_bnode_query.bindings]

        bnode_query = g.query(f"""
            PREFIX dcterms: <http://purl.org/dc/terms/> 
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
            PREFIX geo: <http://www.opengis.net/ont/geosparql#>
            SELECT ?p1 ?p1Label ?p2 ?p2Label ?o2 ?o2Label {{
                <{self.uri}> ?p1 ?o1 .
                ?o1 ?p2 ?o2
                OPTIONAL {{ 
                    {{?p1 rdfs:label ?p1Label}} UNION {{?p1 skos:prefLabel ?p1Label}} UNION {{?p1 dcterms:title ?p1Label}} }}
                OPTIONAL 
                    {{ {{?p2 rdfs:label ?p2Label}} UNION {{?p2 skos:prefLabel ?p2Label}} UNION {{?p2 dcterms:title ?p2Label}} }}
                OPTIONAL {{ 
                    {{?o2 rdfs:label ?o2Label}} UNION {{?o2 skos:prefLabel ?o2Label}} UNION {{?o2 dcterms:title ?o2Label}} }}
                FILTER(ISBLANK(?o1))
                FILTER(?p1!=geo:hasGeometry)
                }}""")
        bnode_results = [{str(k): v for k, v in i.items()} for i in bnode_query.bindings]

        geom_query = g.query(f"""
            PREFIX dcterms: <http://purl.org/dc/terms/> 
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX geo: <http://www.opengis.net/ont/geosparql#>
            SELECT ?p1 ?p1Label ?p2 ?p2Label ?o2 ?o2Label {{
                <{self.uri}> ?p1 ?o1 .
                ?o1 ?p2 ?o2
                OPTIONAL {{ 
                    {{?p1 rdfs:label ?p1Label}} UNION {{?p1 skos:prefLabel ?p1Label}} UNION {{?p1 dcterms:title ?p1Label}} }}
                OPTIONAL 
                    {{ {{?p2 rdfs:label ?p2Label}} UNION {{?p2 skos:prefLabel ?p2Label}} UNION {{?p2 dcterms:title ?p2Label}} }}
                OPTIONAL {{ 
                    {{?o2 rdfs:label ?o2Label}} UNION {{?o2 skos:prefLabel ?o2Label}} UNION {{?o2 dcterms:title ?o2Label}} }}
                FILTER(ISBLANK(?o1))
                FILTER(?p1=geo:hasGeometry)
                }}""")
        geom_results = [{str(k): v for k, v in i.items()} for i in geom_query.bindings]

        # add prefixed URIs (e.g. "skos:prefLabel") to the properties (for display as tooltips in the UI)
        for result_set in [non_bnode_results, bnode_results, geom_results]:
            for property in result_set:
                for k, v in property.copy().items():
                    if isinstance(v, URIRef):
                        property[f"{k}Prefixed"] = v.n3(graph_namespaces.namespace_manager)

        # for bnodes,
        # 1. collect "property 1's"
        # 2. create a dicitonary per property 1
        # (within this dictionary:)
        # 3. add the property 1's attributes
        # 4. add the property 1's (1:many) values as a list
        p1_vals = []
        for result in bnode_results:
            p1_vals.append(result['p1'])
        unique_p1_vals = list(set(p1_vals))
        new_bnode_results = {}
        for val in unique_p1_vals:
            new_bnode_results[val] = {"nestedItems": []}
            for result in bnode_results:
                if result['p1'] == val:
                    new_bnode_results[val]["nestedItems"].append({k:v for k,v in result.items() if k != 'p1'})
                    if 'p1Prefixed' in result.keys():
                        new_bnode_results[val]["p1Prefixed"] = result["p1Prefixed"]
                    if 'p1Label' in result.keys():
                        new_bnode_results[val]["p1Label"] = result["p1Label"]

        self.properties = [i for i in non_bnode_results]
        self.bnode_properties = new_bnode_results
        # for property in non_bnode_results:
        #     keys = [key for key in non_bnode_results[0].keys()]
        #     self.properties[property['pred']] = {}
        #         if

        # non_bnodes = [i for i in feature_graph.triples((None, None, None))
        #               if not (isinstance(i[0], BNode) or isinstance(i[2], BNode))]
        # bnodes = [i for i in feature_graph.triples((None, None, None))
        #               if isinstance(i[2], BNode)]
        #
        # # get the pref labels from a context source - such as the ontology, taxonomies
        # labels_from_context = {}
        # for triple in non_bnodes:
        #     label = context.label(triple[1])
        #     prefLabel = context.preferredLabel(triple[1])
        #     if label:
        #         labels_from_context[triple[1]] = str(label[0][1])
        #     elif prefLabel:
        #         labels_from_context[triple[1]] = str(prefLabel[0][1])
        #
        # labels = dict(ChainMap(defined_labels, labels_from_context))
        # generate property pairs
        # for triple in non_bnodes:
        #     if triple[1] in labels.keys():
        #         self.properties[triple[1]] = {"val": triple[2],
        #                                       "name": labels[triple[1]],
        #                                       "prefixedURI": triple[1].n3(feature_graph.namespace_manager)}
        #     else:
        #         self.properties[triple[1]] = {"val": triple[2]}

        self.identifier = graph_namespaces.value(URIRef(self.uri), DCTERMS.identifier)
        self.title = graph_namespaces.value(URIRef(self.uri), DCTERMS.title)
        self.description = graph_namespaces.value(URIRef(self.uri), DCTERMS.description)
        self.label = graph_namespaces.value(URIRef(self.uri), RDFS.label)
        self.isPartOf = graph_namespaces.value(URIRef(self.uri), DCTERMS.isPartOf)
        if not self.title:
            if self.label:
                self.title = self.label
            else:
                self.title = f"Feature {self.identifier}"

        # Feature geometries
        # out of band call for Geometries as BNodes not supported by SPARQLStore
        # q = f"""
        #     PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        #     SELECT *
        #     WHERE {{
        #         <{self.uri}>
        #             geo:hasGeometry/geo:asWKT ?g1 .
        #            OPTIONAL {{ <{self.uri}> geo:hasGeometry/geo:asDGGS ?g2 . }}
        #     }}
        #     """

        # logging.info(f"SparQL Endpoint: {SPARQL_ENDPOINT}")
        # logging.info(f"Uri feature: {self.uri}")
        # logging.info(f"Query feature: {q}")
        geom_names = {
            'WKT': {"name": "Well Known Text Geometry", "crs": CRS.WGS84},
            'DGGS': {"name": "TB16Pix Geometry", "crs": CRS.TB16PIX},
            'GeoJSON': {"name": "GeoJSON Geometry", "crs": CRS.WGS84}}
        geom_bnode = graph_namespaces.value(URIRef(self.uri), GEO.hasGeometry)
        for geom_type in ['WKT', 'DGGS', 'GeoJSON']:
            geom_literal = graph_namespaces.value(geom_bnode, GEO[f'as{geom_type}'])
            if geom_literal:
                #TODO temporary while geometries contain type at front
                if geom_literal.find('>') > 0:
                    geom_literal = geom_literal.split('> ')[1]
                #TODO only use the truncated geom literal in the HTML pages
                self.geometries.append(Geometry(geom_literal,
                                                GeometryRole.Boundary,
                                                geom_names[geom_type]["name"],
                                                geom_names[geom_type]["crs"]))
        # try:
        #     sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        #     sparql.setQuery(q)
        #     sparql.setReturnFormat(JSON)
        #     ret = sparql.queryAndConvert()["results"]["bindings"]
        #     self.geometries = []
        #     if 'g1' in ret[0].keys(): # TODO come up with a better solution than splitting the string on '> '
        #         self.geometries.append(Geometry(ret[0]["g1"]["value"].split('> ')[1], GeometryRole.Boundary, "WGS84 Geometry", CRS.WGS84))
        #     if 'g2' in ret[0].keys():
        #         self.geometries.append(Geometry(ret[0]["g2"]["value"], GeometryRole.Boundary, "TB16Pix Geometry", CRS.TB16PIX))
        #     # self.geometries = [
        #     #     Geometry(ret[0]["g1"]["value"], GeometryRole.Boundary, "WGS84 Geometry", CRS.WGS84),
        #     #     Geometry(ret[0]["g2"]["value"], GeometryRole.Boundary, "TB16Pix Geometry", CRS.TB16PIX),
        #     # ]
        #     logging.info(f"Geometries - {self.geometries}")
        # except Exception as e:
        #     logging.error(e)

        # Feature other properties
        self.extent_spatial = None
        self.extent_temporal = None
        self.links = [
            Link(LANDING_PAGE_URL + "/collections/" + self.identifier + "/items",
                 rel=RelType.ITEMS.value,
                 type=MediaType.GEOJSON.value,
                 title=self.title)
        ]
        if other_links is not None:
            self.links.extend(other_links)

    def to_dict(self):
        self.links = [x.__dict__ for x in self.links]
        if self.geometries is not None:
            self.geometries = [x.to_dict() for x in self.geometries]
        return self.__dict__

    def to_geo_json_dict(self):
        # this only serialises the Feature properties and WGS84 Geometries
        """
        {
          "type": "Feature",
          "geometry": {
            "type": "LineString",
            "coordinates": [
              [102.0, 0.0], [103.0, 1.0], [104.0, 0.0], [105.0, 1.0]
            ]
          },
        """
        # TODO might make more sense to put the geometries in to a dictionary, to avoid the list comps below
        available_geoms = [g.label for g in self.geometries]
        if "GeoJSON Geometry" in available_geoms:
            geojson_geometry = [g.coordinates for g in self.geometries if g.label == "GeoJSON Geometry"][0]
        else:
            geojson_geometry = [g.to_geo_json_dict() for g in self.geometries if g.label == "Well Known Text Geometry"][0]  # one only

        properties = {
            "title": self.title,
            "isPartOf": self.isPartOf
        }
        if self.description is not None:
            properties["description"] = self.description

        return {
            "id": self.uri,
            "type": "Feature",
            "geometry": rewind(geojson_geometry),
            "properties": properties
        }

    def to_geosp_graph(self):
        local_g = Graph()

        local_g.bind("geo", GEO)
        local_g.bind("geox", GEOX)

        f = URIRef(self.uri)
        local_g.add((
            f,
            RDF.type,
            GEO.Feature
        ))
        for geom in self.geometries:
            this_geom = BNode()
            local_g.add((
                f,
                GEO.hasGeometry,
                this_geom
            ))
            local_g.add((
                this_geom,
                RDFS.label,
                Literal(geom.label)
            ))
            local_g.add((
                this_geom,
                GEOX.hasRole,
                URIRef(geom.role.value)
            ))
            local_g.add((
                this_geom,
                GEOX.inCRS,
                URIRef(geom.crs.value)
            ))
            if geom.crs == CRS.TB16PIX:
                local_g.add((
                    this_geom,
                    GEOX.asDGGS,
                    Literal(geom.coordinates, datatype=GEOX.DggsLiteral)
                ))
            else:  # WGS84
                local_g.add((
                    this_geom,
                    GEO.asWKT,
                    Literal(geom.coordinates, datatype=GEO.WktLiteral)
                ))

        return local_g


class FeatureRenderer(Renderer):
    def __init__(self, request, feature_uri: str, collection_id: str, other_links: List[Link] = None):
        self.feature = Feature(feature_uri)
        self.links = []
        if other_links is not None:
            self.links.extend(other_links)

        super().__init__(
            request=request,
            instance_uri=LANDING_PAGE_URL + "/collections/" + collection_id + "/items/" + self.feature.identifier,
            profiles={"oai": profile_openapi, "geosp": profile_geosparql},
            default_profile_token="oai",
            MEDIATYPE_NAMES=MEDIATYPE_NAMES
        )

        self.ALLOWED_PARAMS = ["_profile", "_view", "_mediatype", "version"]

    def render(self):
        for v in self.request.query_params.items():
            if v[0] not in self.ALLOWED_PARAMS:
                return Response("The parameter {} you supplied is not allowed".format(v[0]), status=400)

        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "oai":
            if self.mediatype == MediaType.JSON.value:
                return self._render_oai_json()
            elif self.mediatype == MediaType.GEOJSON.value:
                return self._render_oai_geojson()
            else:
                return self._render_oai_html()
        elif self.profile == "geosp":
            return self._render_geosp_rdf()

    def _render_oai_json(self):
        page_json = {
            "links": [x.__dict__ for x in self.links],
            "feature": self.feature.to_geo_json_dict()
        }

        return JSONResponse(
            page_json,
            media_type=str(MediaType.JSON.value),
            headers=self.headers,
        )

    def _render_oai_geojson(self):
        page_json = self.feature.to_geo_json_dict()
        if len(self.links) > 0:
            page_json["links"] = [x.__dict__ for x in self.links]

        return JSONResponse(
            page_json,
            media_type=str(MediaType.GEOJSON.value),
            headers=self.headers,
        )

    def _render_oai_html(self):
        _template_context = {
            "links": self.links,
            "feature": self.feature,
            "request": self.request
        }

        return templates.TemplateResponse(name="feature.html",
                                          context=_template_context,
                                          headers=self.headers)

    def _render_geosp_rdf(self):
        g = self.feature.to_geosp_graph()

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return JSONResponse(g.serialize(format="json-ld"), media_type=self.mediatype, headers=self.headers)
        elif self.mediatype in Renderer.RDF_MEDIA_TYPES:
            return PlainTextResponse(g.serialize(format=self.mediatype), media_type=self.mediatype, headers=self.headers)
        else:
            return Response(
                "The Media Type you requested cannot be serialized to",
                status_code=400,
                media_type="text/plain"
            )
