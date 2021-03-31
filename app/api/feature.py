from typing import List
from api.profiles import *
from api.link import *
import json

from config import *
from utils import utils

from fastapi import Response
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import URIRef, Literal, BNode
from rdflib.namespace import DCTERMS, RDF, RDFS, XSD
from enum import Enum
from geomet import wkt
from geojson_rewind import rewind
import markdown


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

        q = """
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX ogcapi: <https://data.surroundaustralia.com/def/ogcapi/>

            SELECT ?identifier ?title ?description
            WHERE {{
                ?uri a ogcapi:Feature ;
                   dcterms:isPartOf <{}> ;
                   dcterms:identifier ?identifier ;
                   OPTIONAL {{?uri dcterms:title ?title}}
                   OPTIONAL {{?uri dcterms:description ?description}}
            }}
            """  # .format(collection_id)
        # g = get_graph()
        # Feature properties
        self.description = None
        for p, o in g.predicate_objects(subject=URIRef(self.uri)):
            if p == DCTERMS.identifier:
                self.identifier = str(o)
            elif p == DCTERMS.title:
                self.title = str(o)
            elif p == DCTERMS.description:
                self.description = markdown.markdown(str(o))
            elif p == DCTERMS.isPartOf:
                self.isPartOf = str(o)

        # Feature geometries
        # out of band call for Geometries as BNodes not supported by SPARQLStore
        q = """
            PREFIX geo: <http://www.opengis.net/ont/geosparql#>
            PREFIX geox: <https://linked.data.gov.au/def/geox#>
            SELECT * 
            WHERE {{
                <{}>
                    geo:hasGeometry/geo:asWKT ?g1 ;
                    geo:hasGeometry/geox:asDGGS ?g2 .
            }}
            """.format(self.uri)

        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        ret = sparql.queryAndConvert()["results"]["bindings"]
        self.geometries = [
            Geometry(ret[0]["g1"]["value"], GeometryRole.Boundary, "WGS84 Geometry", CRS.WGS84),
            Geometry(ret[0]["g2"]["value"], GeometryRole.Boundary, "TB16Pix Geometry", CRS.TB16PIX),
        ]

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
        geojson_geometry = [g.to_geo_json_dict() for g in self.geometries if g.crs == CRS.WGS84][0]  # one only

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
        # g = Graph()
        g.bind("geo", GEO)
        g.bind("geox", GEOX)

        f = URIRef(self.uri)
        g.add((
            f,
            RDF.type,
            GEO.Feature
        ))
        for geom in self.geometries:
            this_geom = BNode()
            g.add((
                f,
                GEO.hasGeometry,
                this_geom
            ))
            g.add((
                this_geom,
                RDFS.label,
                Literal(geom.label)
            ))
            g.add((
                this_geom,
                GEOX.hasRole,
                URIRef(geom.role.value)
            ))
            g.add((
                this_geom,
                GEOX.inCRS,
                URIRef(geom.crs.value)
            ))
            if geom.crs == CRS.TB16PIX:
                g.add((
                    this_geom,
                    GEOX.asDGGS,
                    Literal(geom.coordinates, datatype=GEOX.DggsLiteral)
                ))
            else:  # WGS84
                g.add((
                    this_geom,
                    GEO.asWKT,
                    Literal(geom.coordinates, datatype=GEO.WktLiteral)
                ))

        return g


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
            return JSONResponse(g.serialize(format="json-ld").decode(), media_type=self.mediatype, headers=self.headers)
        elif self.mediatype in Renderer.RDF_MEDIA_TYPES:
            return JSONResponse(g.serialize(format=self.mediatype).decode(), media_type=self.mediatype, headers=self.headers)
        else:
            return Response(
                "The Media Type you requested cannot be serialized to",
                status_code=400,
                media_type="text/plain"
            )
