from typing import List

from fastapi import Response
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from geojson_rewind import rewind
from geomet import wkt
from rdflib import Graph
from rdflib import URIRef, Literal, BNode
from rdflib.namespace import DCTERMS, RDF, RDFS

from api.link import *
from api.profiles import *
from config import *
from utils import utils

templates = Jinja2Templates(directory="templates")
g = utils.g


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
        self.geometries = {}

        # get graph namespaces + geosparql namespaces as we want their prefixes for display
        # self.graph_namespaces = geo_context
        self.graph_namespaces = g.query(f"""DESCRIBE <{self.uri}>""").graph
        # self.graph_namespaces.bind('geo', Namespace('http://www.opengis.net/ont/geosparql#'))

        non_bnode_query = g.query(f"""
            PREFIX dcterms: <http://purl.org/dc/terms/> 
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
            SELECT ?p1 ?p1Label ?o1 ?o1Label {{
                <{self.uri}> ?p1 ?o1 
                OPTIONAL {{ 
                    {{?p1 rdfs:label ?p1Label}} UNION {{?p1 skos:p1Label ?predLabel}} UNION {{?p1 dcterms:title ?p1Label}} 
                        FILTER(lang(?p1Label) = "" || lang(?p1Label) = "en") }}
                OPTIONAL {{ 
                    {{?o1 rdfs:label ?o1Label}} UNION {{?o1 skos:prefLabel ?o1Label}} UNION {{?o1 dcterms:title ?o1Label}}
                        FILTER(lang(?o1Label) = "" || lang(?o1Label) = "en") }}
                FILTER(!ISBLANK(?o1))
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
                    {{?p1 rdfs:label ?p1Label}} UNION {{?p1 skos:prefLabel ?p1Label}} UNION {{?p1 dcterms:title ?p1Label}} 
                        FILTER(lang(?p1Label) = "" || lang(?p1Label) = "en") }}
                OPTIONAL 
                    {{ {{?p2 rdfs:label ?p2Label}} UNION {{?p2 skos:prefLabel ?p2Label}} UNION {{?p2 dcterms:title ?p2Label}} 
                        FILTER(lang(?p2Label) = "" || lang(?p2Label) = "en") }}
                OPTIONAL {{ 
                    {{?o2 rdfs:label ?o2Label}} UNION {{?o2 skos:prefLabel ?o2Label}} UNION {{?o2 dcterms:title ?o2Label}}
                        FILTER(lang(?o2Label) = "" || lang(?o2Label) = "en") }}
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
                    {{?p1 rdfs:label ?p1Label}} UNION {{?p1 skos:prefLabel ?p1Label}} UNION {{?p1 dcterms:title ?p1Label}}
                        FILTER(lang(?p1Label) = "" || lang(?p1Label) = "en") }}
                OPTIONAL 
                    {{ {{?p2 rdfs:label ?p2Label}} UNION {{?p2 skos:prefLabel ?p2Label}} UNION {{?p2 dcterms:title ?p2Label}} 
                        FILTER(lang(?p2Label) = "" || lang(?p2Label) = "en") }}
                OPTIONAL {{ 
                    {{?o2 rdfs:label ?o2Label}} UNION {{?o2 skos:prefLabel ?o2Label}} UNION {{?o2 dcterms:title ?o2Label}} 
                        FILTER(lang(?o2Label) = "" || lang(?o2Label) = "en") }}
                FILTER(ISBLANK(?o1))
                FILTER(?p1=geo:hasGeometry)
                }}""")
        geom_results = [{str(k): v for k, v in i.items()} for i in geom_query.bindings]

        # add prefixed URIs (e.g. "skos:prefLabel") to the properties (for display as tooltips in the UI)
        for result_set in [non_bnode_results, bnode_results, geom_results]:
            for property in result_set:
                for k, v in property.copy().items():
                    if isinstance(v, URIRef):
                        property[f"{k}Prefixed"] = v.n3(self.graph_namespaces.namespace_manager)
                # keys = property.keys()
                # for node in ['p1', 'p2', 'o1', 'o2']:
                #     if node in keys and f'{node}Label' not in keys:
                #         label = self.get_label(property[node])
                #         if label:
                #             property[f"{node}Label"] = label
                # check for p1 label, if not, use function to try find one from context
                # if o1 / p2 / o2 in proerty.keys()
                # use function to check for label with these

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
                    new_bnode_results[val]["nestedItems"].append({k: v for k, v in result.items() if k != 'p1'})
                    if 'p1Prefixed' in result.keys():
                        new_bnode_results[val]["p1Prefixed"] = result["p1Prefixed"]
                    if 'p1Label' in result.keys():
                        new_bnode_results[val]["p1Label"] = result["p1Label"]

        self.properties = [i for i in non_bnode_results]
        self.bnode_properties = new_bnode_results

        self.identifier = self.graph_namespaces.value(URIRef(self.uri), DCTERMS.identifier)
        self.title = self.graph_namespaces.value(URIRef(self.uri), DCTERMS.title)
        self.description = self.graph_namespaces.value(URIRef(self.uri), DCTERMS.description)
        self.label = self.graph_namespaces.value(URIRef(self.uri), RDFS.label)
        self.isPartOf = self.graph_namespaces.value(URIRef(self.uri), DCTERMS.isPartOf)
        if not self.title:
            if self.label:
                self.title = self.label
            else:
                self.title = f"Feature {self.identifier}"

        geom_names = {
            'asWKT': {"crs": CRS.WGS84},
            'asDGGS': {"crs": CRS.TB16PIX},
            'asGeoJSON': {"crs": CRS.WGS84}
            }

        for result in geom_results:
            geom_type = result["p2"].split('#')[1]
            geom_literal = result["o2"]
            if geom_literal.find('>') > 0:
                geom_literal = geom_literal.split('> ')[1]
            self.geometries[geom_type] = Geometry(
                geom_literal,
                GeometryRole.Boundary,
                result["p2Label"],
                geom_names[geom_type]["crs"]
                )

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
            self.geometries = {k: v.to_dict() for k, v in self.geometries.items()}
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
        if "GeoJSON" in self.geometries.keys():
            geojson_geometry = self.geometries["GeoJSON"].coordinates
        else:
            geojson_geometry = self.geometries["WKT"].to_geo_json_dict()

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
        for geom in self.geometries.values():
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

    # def get_label(self, node):
    #     preflabel_from_context = self.graph_namespaces.preferredLabel(node)
    #     label_from_context = self.graph_namespaces.label(node)
    #     if preflabel_from_context:
    #         return preflabel_from_context[0][1]
    #     elif label_from_context:
    #         return label_from_context[0][1]


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
        if "asGeoJSON" not in self.feature.geometries.keys():
            self.feature.geometries["asGeoJSON"] = self.feature.to_geo_json_dict

        _template_context = {
            "links": self.links,
            "feature": self.feature,
            "request": self.request,
            "api_title": f"{self.feature.title} - {API_TITLE}"
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
            return PlainTextResponse(g.serialize(format=self.mediatype), media_type=self.mediatype,
                                     headers=self.headers)
        else:
            return Response(
                "The Media Type you requested cannot be serialized to",
                status_code=400,
                media_type="text/plain"
                )
