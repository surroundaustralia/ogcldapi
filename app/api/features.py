import re
from typing import List

from SPARQLWrapper import SPARQLWrapper, JSON
from fastapi import Response
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pyldapi import ContainerRenderer
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, XSD, RDF

from api.collection import Collection
from api.feature import Feature
from api.link import *
from api.profiles import *
from config import *
from utils import utils
from utils.sparql_queries import feature_class_label_sparql

templates = Jinja2Templates(directory="templates")
g = utils.g


class FeaturesList:
    def __init__(self, request, collection_id):
        self.request = request
        self.page = (
            int(request.query_params.get("page"))
            if request.query_params.get("page") is not None
            else 1
        )
        self.per_page = (
            int(request.query_params.get("per_page"))
            if request.query_params.get("per_page") is not None
            else 100
        )

        # get Collection
        self.collection = Collection
        result = g.query(
            f"""PREFIX dcterms: <http://purl.org/dc/terms/> 
                SELECT ?collection 
                {{?collection dcterms:identifier "{collection_id}"^^xsd:token}}
                """
        )
        collection = str(list(result.bindings[0].values())[0])
        self.collection = Collection(collection)

        # filter if we have a filtering param
        if request.query_params.get("bbox") is not None:
            # work out what sort of BBOX filter it is and filter by that type
            features_uris = self.get_feature_uris_by_bbox()
        else:
            result = g.query(
                f"""PREFIX dcterms: <http://purl.org/dc/terms/> 
                    SELECT (COUNT(?s) as ?count)
                    {{?s dcterms:isPartOf <{self.collection.uri}>}}"""
            )
        self.feature_count = int(list(result.bindings[0].values())[0])
        self.limit = (
            int(request.query_params.get("limit"))
            if request.query_params.get("limit") is not None
            else None
        )

        result = g.query(
            f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                SELECT ?feature ?identifier ?title ?description
                {{?feature dcterms:isPartOf <{self.collection.uri}> ;
                    dcterms:identifier ?identifier ;
                    OPTIONAL {{?feature rdfs:label ?title}}
                    OPTIONAL {{?feature dcterms:description ?description}}
                }} LIMIT {self.per_page} OFFSET {(self.page - 1) * self.per_page}
                """
        )

        result = [{str(k): v for k, v in i.items()} for i in result.bindings]
        features = [str(i["feature"]) for i in result]
        descriptions = [
            i["description"] if "description" in i.keys() else None for i in result
        ]
        identifiers = [
            str(i["identifier"]) if "identifier" in i.keys() else None for i in result
        ]
        # use the title if it's available, otherwise use "<class_label> {identifier}"

        if "title" in result[0].keys():
            titles = [i["title"] for i in result]
        else:
            # take the class label for the first feature (assuming all features in a feature collection have the same
            # class) to not make this assumption *all* features would have to be queried for their class' label - this
            # would be expensive!
            query_result = g.query(feature_class_label_sparql.substitute({"URI": str(result[0]["feature"])}))
            class_label = str(list(query_result.bindings[0].values())[1])
            titles = [f"{class_label} {i['identifier']}" for i in result]


        self.features = list(zip(features, identifiers, titles, descriptions))
        self.bbox_type = None

    def get_feature_uris_by_bbox(self):
        allowed_bbox_formats = {
            "coords": r"([0-9\.\-]+),([0-9\.\-]+),([0-9\.\-]+),([0-9\.\-]+)",
            # Lat Longs, e.g. 160.6,-55.95,-170,-25.89
            "cell_id": r"([A-Z][0-9]{0,15})$",  # single DGGS Cell ID, e.g. R1234
            "cell_ids": r"([A-Z][0-9]{0,15}),([A-Z][0-9]{0,15})",  # two DGGS cells, e.g. R123,R456
        }
        for k, v in allowed_bbox_formats.items():
            if re.match(v, self.request.query_params.get("bbox")):
                self.bbox_type = k

        if self.bbox_type is None:
            return None
        elif self.bbox_type == "coords":
            return self._get_filtered_features_list_bbox_wgs84()
        elif self.bbox_type == "cell_id":
            return self._get_filtered_features_list_bbox_dggs()
        elif self.bbox_type == "cell_ids":
            pass

    def _get_filtered_features_list_bbox_wgs84(self):
        parts = self.request.query_params.get("bbox").split(",")

        demo = """
            149.041411262992398 -35.292795884738389, 
            149.041411262992398 -35.141378579917053, 
            149.314863045854082 -35.141378579917053,
            149.314863045854082 -35.292795884738389,
            149.041411262992398 -35.292795884738389
            """

        q = """
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX geo: <http://www.opengis.net/ont/geosparql#>
            PREFIX geof: <http://www.opengis.net/def/function/geosparql/>

            SELECT ?f
            WHERE {{
                ?f a geo:Feature ;
                   dcterms:isPartOf <{collection_uri}> ;            
                   geo:hasGeometry/geo:asWKT ?wkt .
    
                FILTER (geof:sfOverlaps(?wkt, 
                    '''
                    <http://www.opengis.net/def/crs/OGC/1.3/CRS84>
                    POLYGON ((
                        {tl_lon} {tl_lat}, 
                        {tl_lon} {br_lat}, 
                        {br_lon} {br_lat},
                        {br_lon} {tl_lat},
                        {tl_lon} {tl_lat}
                    ))
                    '''^^geo:wktLiteral))
            }}
            ORDER BY ?f
            """.format(
            **{
                "collection_uri": self.collection.uri,
                "tl_lon": parts[0],
                "tl_lat": parts[1],
                "br_lon": parts[2],
                "br_lat": parts[3],
            }
        )
        # TODO FILTER
        features_uris = []
        for r in get_graph().query(q):
            features_uris.append(r["f"])

        return features_uris

    def _get_filtered_features_list_bbox_dggs(self):
        # geo:sfOverlaps - any Cell of the Feature is within the BBox
        q = """
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX geo: <http://www.opengis.net/ont/geosparql#>
            PREFIX geox: <https://linked.data.gov.au/def/geox#>

            SELECT ?f
            WHERE {{
                ?f a geo:Feature ;
                   dcterms:isPartOf <{}> .
                ?f geo:hasGeometry/geox:asDGGS ?dggs .

                FILTER CONTAINS(STR(?dggs), "{}")
            }}
            """.format(
            self.collection.uri, self.request.query_params.get("bbox")
        )

        # TODO: update as RDFlib updates
        # for r in get_graph().query(q):
        #     features_uris.append((r["f"], r["prefLabel"]))

        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        ret = sparql.queryAndConvert()["results"]["bindings"]
        return [URIRef(r["f"]["value"]) for r in ret]

        # geo:sfWithin - every Cell of the Feature is within the BBox
        # q = """
        #     PREFIX dcterms: <http://purl.org/dc/terms/>
        #     PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        #     PREFIX geox: <https://linked.data.gov.au/def/geox#>
        #
        #     SELECT ?f ?coords
        #     WHERE {{
        #         ?f a geo:Feature ;
        #            dcterms:isPartOf <{}> .
        #         ?f geo:hasGeometry/geox:asDGGS ?dggs .
        #
        #         BIND (STRBEFORE(STRAFTER(STR(?dggs), "POLYGON ("), ")")AS ?coords)
        #     }}
        #     """.format(self.collection.uri)
        # from SPARQLWrapper import SPARQLWrapper, JSON
        # sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        # sparql.setQuery(q)
        # sparql.setReturnFormat(JSON)
        # ret = sparql.queryAndConvert()["results"]["bindings"]
        # feature_ids = []
        # for r in ret:
        #     within = True
        #     for cell in r["coords"]["value"].split(" "):
        #         if not str(cell).startswith(self.request.query_params.get("bbox")):
        #             within = False
        #             break
        #     if within:
        #         feature_ids.append(URIRef(r["f"]["value"]))
        #
        # return feature_ids

    def _get_filtered_features_list_bbox_paging(self):
        pass


class FeaturesRenderer(ContainerRenderer):
    def __init__(self, request, collection_id, other_links: List[Link] = None):
        self.request = request
        self.valid = self._valid_parameters()
        if self.valid[0]:
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

            self.feature_list = FeaturesList(request, collection_id)

            super().__init__(
                request,
                LANDING_PAGE_URL
                + "/collections/"
                + self.feature_list.collection.identifier
                + "/items",
                "Features",
                "The Features of Collection {}".format(
                    self.feature_list.collection.identifier
                ),
                None,
                None,
                [
                    (
                        LANDING_PAGE_URL
                        + "/collections/"
                        + self.feature_list.collection.identifier
                        + "/items/"
                        + x[1],
                        x[2],
                    )
                    for x in self.feature_list.features
                ],
                self.feature_list.feature_count,
                profiles={"oai": profile_openapi, "geosp": profile_geosparql},
                default_profile_token="oai",
            )

            # overridden in ContinerRenderer in pyldapi, need to re-set here
            self.per_page = (
                int(request.query_params.get("per_page"))
                if request.query_params.get("per_page") is not None
                else 100
            )

            # override last_page variable (pyldapi's last_page calculation is incorrect)
            ceiling = lambda a, b: a // b + bool(a % b)
            self.last_page = ceiling(self.feature_list.feature_count, self.per_page)

    def _valid_parameters(self):
        allowed_params = [
            "_profile",
            "_view",
            "_mediatype",
            "_format",
            "page",
            "per_page",
            "limit",
            "bbox",
        ]

        allowed_bbox_formats = [
            r"([0-9\.\-]+),([0-9\.\-]+),([0-9\.\-]+),([0-9\.\-]+)",  # Lat Longs, e.g. 160.6,-55.95,-170,-25.89
            r"([A-Z][0-9]{0,15})$",  # single DGGS Cell ID, e.g. R1234
            r"([A-Z][0-9]{0,15}),([A-Z][0-9]{0,15})",  # two DGGS cells, e.g. R123,R456
        ]

        for p in self.request.query_params.keys():
            if p not in allowed_params:
                return (
                    False,
                    "The parameter {} you supplied is not allowed. "
                    "For this API endpoint, you may only use one of '{}'".format(
                        p, "', '".join(allowed_params)
                    ),
                )

        if self.request.query_params.get("limit") is not None:
            try:
                int(self.request.query_params.get("limit"))
            except ValueError:
                return (
                    False,
                    "The parameter 'limit' you supplied is invalid. It must be an integer",
                )

        if self.request.query_params.get("bbox") is not None:
            for p in allowed_bbox_formats:
                if re.match(p, self.request.query_params.get("bbox")):
                    return True, None
            return (
                False,
                "The parameter 'bbox' you supplied is invalid. Must be either two pairs of long/lat values, "
                "a DGGS Cell ID or a pair of DGGS Cell IDs",
            )

        return True, None

    def render(self):
        # return without rendering anything if there is an error with the parameters
        if not self.valid[0]:
            return Response(
                self.valid[1], status=400, mimetype="text/plain", headers=self.headers
            )

        # try returning alt profile
        template_context = {
            "api_title": f"Features in {self.feature_list.collection.title} - {API_TITLE}",
            "theme": THEME
        }
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
            if self.mediatype == MediaType.HTML.value:
                return self._render_oai_html()
            else:
                return self._render_geosp_rdf()

    def _render_oai_json(self):
        page_json = {
            "links": [x.__dict__ for x in self.links],
            "collection": self.feature_list.collection.to_dict(),
            "items": self.members,
        }

        return JSONResponse(
            page_json,
            media_type=str(MediaType.JSON.value),
            headers=self.headers,
        )

    def _render_oai_geojson(self):
        page_json = {
            "links": [x.__dict__ for x in self.links],
            "collection": self.feature_list.collection.to_geo_json_dict(),
            "items": self.members,
        }

        return JSONResponse(
            page_json,
            media_type=str(MediaType.GEOJSON.value),
            headers=self.headers,
        )

    def _render_oai_html(self):
        # generate link QSAs from the FeaturesRenderer attributes
        links = {}
        for link_type in ["first_page", "next_page", "prev_page", "last_page"]:
            page = getattr(self, link_type)
            if page:
                links[
                    link_type
                ] = f"{self.instance_uri}?per_page={self.per_page}&page={page}"

        _template_context = {
            "links": self.links,
            "collection": self.feature_list.collection,
            "members_total_count": self.members_total_count,
            "page_links": links,
            "members": sorted(self.members, key=lambda m: m[1]),
            "request": self.request,
            "pageSize": self.per_page,
            "pageNumber": self.page,
            "api_title": f"Features in {self.feature_list.collection.title} - {API_TITLE}",
            "theme": THEME
        }

        if (
            self.request.query_params.get("bbox") is not None
        ):  # it it exists at this point, it must be valid
            _template_context["bbox"] = (
                self.feature_list.bbox_type,
                self.request.query_params.get("bbox"),
            )

        return templates.TemplateResponse(
            name="features.html", context=_template_context, headers=self.headers
        )

    def _render_geosp_rdf(self):
        g = Graph()

        LDP = Namespace("http://www.w3.org/ns/ldp#")
        g.bind("ldp", LDP)

        XHV = Namespace("https://www.w3.org/1999/xhtml/vocab#")
        g.bind("xhv", XHV)

        page_uri_str = (
            self.request.uri
            + "?per_page="
            + str(self.per_page)
            + "&page="
            + str(self.page)
        )
        page_uri_str_nonum = (
            self.request.uri + "?per_page=" + str(self.per_page) + "&page="
        )
        page_uri = URIRef(page_uri_str)

        # pagination
        # this page
        g.add((page_uri, RDF.type, LDP.Page))
        g.add((page_uri, LDP.pageOf, URIRef(self.feature_list.collection.uri)))

        # links to other pages
        g.add((page_uri, XHV.first, URIRef(page_uri_str_nonum + "1")))
        g.add((page_uri, XHV.last, URIRef(page_uri_str_nonum + str(self.last_page))))

        if self.page != 1:
            g.add((page_uri, XHV.prev, URIRef(page_uri_str_nonum + str(self.page - 1))))

        if self.page != self.last_page:
            g.add((page_uri, XHV.next, URIRef(page_uri_str_nonum + str(self.page + 1))))

        g = g + self.feature_list.collection.to_geosp_graph()
        g.add(
            (
                URIRef(self.feature_list.collection.uri),
                GEOX.featureCount,
                Literal(self.feature_list.feature_count, datatype=XSD.integer),
            )
        )

        for f in self.feature_list.features:
            g = g + Feature(f[0]).to_geosp_graph()
            g.add(
                (
                    URIRef(f[0]),
                    DCTERMS.isPartOf,
                    URIRef(self.feature_list.collection.uri),
                )
            )

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return JSONResponse(
                g.serialize(format="json-ld"),
                media_type=self.mediatype,
                headers=self.headers,
            )
        elif self.mediatype in Renderer.RDF_MEDIATYPES:
            return Response(
                g.serialize(format=self.mediatype),
                media_type=self.mediatype,
                headers=self.headers,
            )
        else:
            return Response(
                "The Media Type you requested cannot be serialized to",
                status_code=400,
                media_type="text/plain",
            )
