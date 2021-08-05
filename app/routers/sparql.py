from typing import Optional, List

import io
import fastapi
import logging
import requests
from urllib.parse import unquote, parse_qs
from fastapi import Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response, RedirectResponse
from pyldapi import Renderer, RDF_MEDIATYPES
from rdflib import Graph

from api.sparql import SparqlRenderer
from config import *

router = fastapi.APIRouter()
templates = Jinja2Templates(directory="templates")

def _best_match(types: List[str], accept: str, default: Optional[str] = None) -> str:
    """Emulates the behaviour of Flask's best_match() method"""
    best_quality = -1
    result = default

    # build list of tuples [(mime_type, quality), ...]
    accept_tup = []
    for accept_header in accept.split(","):
        mime_type = ""
        quality = 1
        if ";q=" in mime_type:
            [mime_type, quality] = accept_header.split(";q=")
        else:
            mime_type = accept_header
        accept_tup.append((mime_type, quality))
    
    # loop through types and find highest quality value
    for mime_type, quality in accept_tup:
        if mime_type in types and quality > best_quality:
            result = mime_type
            best_quality = quality

    return result

def _form_urlencoded_to_dict(body: bytes) -> dict:
    """Creates a dict from a form-urlencoded body"""
    return {key: value[0] for key, value in parse_qs(body.decode()).items()}


@router.get(
    "/sparql",
    summary="SPARQL Endpoint",
    responses={
        200: {"description": "SPARQL page correctly loaded."},
        400: {"description": "Parameter not found or not valid."},
    },
)
@router.post(
    "/sparql",
    summary="SPARQL Endpoint",
    responses={
        200: {"description": "SPARQL page correctly loaded."},
        400: {"description": "Parameter not found or not valid."},
    },
)
async def sparql(
    request: Request,
    _view: Optional[str] = None,
    _profile: Optional[str] = None,
    _format: Optional[str] = None,
    _mediatype: Optional[str] = None,
    version: Optional[str] = None,
):

    SPARQL_RESPONSE_MEDIA_TYPES = [
        "application/sparql-results+json",
        "text/csv",
        "text/tab-separated-values",
    ]
    QUERY_RESPONSE_MEDIA_TYPES = ["text/html"] + SPARQL_RESPONSE_MEDIA_TYPES + RDF_MEDIATYPES
    accept_type = _best_match(QUERY_RESPONSE_MEDIA_TYPES, request.headers["accept"], "text/html")
    logging.debug("accept_type: " + accept_type)

    try:
        if accept_type in SPARQL_RESPONSE_MEDIA_TYPES or accept_type in RDF_MEDIATYPES:
            # return data
            logging.info("returning endpoint()")
            return await endpoint(request)
        else:
            # return HTML UI
            logging.info(f"Sparql page request: {request.path_params}")
            render_content = SparqlRenderer(request).render()
            return render_content
    except Exception as e:
        return HTTPException(detail=e, status_code=500)

@router.get(
    "/endpoint",
    summary="SPARQL Endpoint",
    responses={
        200: {"description": "SPARQL page correctly loaded."},
        400: {"description": "Parameter not found or not valid."},
    },
)
@router.post(
    "/endpoint",
    summary="SPARQL Endpoint",
    responses={
        200: {"description": "SPARQL page correctly loaded."},
        400: {"description": "Parameter not found or not valid."},
    },
)
async def endpoint(
    request: Request,
    _view: Optional[str] = None,
    _profile: Optional[str] = None,
    _format: Optional[str] = None,
    _mediatype: Optional[str] = None,
    version: Optional[str] = None,
):
    logging.info("request: {}".format(request.__dict__))

    def get_sparql_service_description(rdf_fmt="turtle"):
        """Return an RDF description of PROMS' read only SPARQL endpoint in a requested format
        :param rdf_fmt: 'turtle', 'n3', 'xml', 'json-ld'
        :return: string of RDF in the requested format
        """
        sd_ttl = """
            @prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix sd:     <http://www.w3.org/ns/sparql-service-description#> .
            @prefix sdf:    <http://www.w3.org/ns/formats/> .
            @prefix void:   <http://rdfs.org/ns/void#> .
            @prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .
            <{0}>
                a                       sd:Service ;
                sd:endpoint             <{0}> ;
                sd:supportedLanguage    sd:SPARQL11Query ; # yes, read only, sorry!
                sd:resultFormat         sdf:SPARQL_Results_JSON ;  # yes, we only deliver JSON results, sorry!
                sd:feature sd:DereferencesURIs ;
                sd:defaultDataset [
                    a sd:Dataset ;
                    sd:defaultGraph [
                        a sd:Graph ;
                        void:triples "100"^^xsd:integer
                    ]
                ]
            .
        """.format(SparqlRenderer.instance_uri)
        grf = Graph().parse(io.StringIO(sd_ttl), format="turtle")
        rdf_formats = list(set([x for x in Renderer.RDF_SERIALIZER_TYPES_MAP]))
        if rdf_fmt in rdf_formats:
            return grf.serialize(format=rdf_fmt)
        else:
            raise ValueError(
                "Input parameter rdf_format must be one of: " + ", ".join(rdf_formats)
            )

    def sparql_query2(q, media_type="application/json"):
        """ Make a SPARQL query"""
        logging.debug("sparql_query2: {}".format(q))
        data = q

        headers = {
            "Content-Type": "application/sparql-query",
            "Accept": media_type,
            "Accept-Encoding": "UTF-8",
        }
        if SPARQL_USERNAME is not None and SPARQL_PASSWORD is not None:
            auth = (SPARQL_USERNAME, SPARQL_PASSWORD)
        else:
            auth = None

        try:
            logging.debug(
                "endpoint={}\ndata={}\nheaders={}".format(
                    SPARQL_ENDPOINT, data, headers
                )
            )
            
            if auth is not None:
                r = requests.post(
                    SPARQL_ENDPOINT, auth=auth, data=data, headers=headers, timeout=60
                )
            else:
                r = requests.post(
                    SPARQL_ENDPOINT, data=data, headers=headers, timeout=60
                )
            
            logging.debug("response: {}".format(r.__dict__))
            return r.content.decode("utf-8")
        except Exception as ex:
            raise ex

    format_mimetype = request.headers["ACCEPT"]

    # Query submitted
    if request.method == "POST":
        """Pass on the SPARQL query to the underlying endpoint defined in config"""
        if "application/x-www-form-urlencoded" in request.headers["content-type"]:
            request_body = _form_urlencoded_to_dict(await request.body())
            """
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-post-urlencoded
            2.1.2 query via POST with URL-encoded parameters
            Protocol clients may send protocol requests via the HTTP POST method by URL encoding the parameters. When
            using this method, clients must URL percent encode all parameters and include them as parameters within the
            request body via the application/x-www-form-urlencoded media type with the name given above. Parameters must
            be separated with the ampersand (&) character. Clients may include the parameters in any order. The content
            type header of the HTTP request must be set to application/x-www-form-urlencoded.
            """
            if (
                    request_body.get("query") is None
                    or len(request_body.get("query")) < 5
            ):
                return Response(
                    "Your POST request to the SPARQL endpoint must contain a 'query' parameter if form posting "
                    "is used.",
                    status_code=400,
                    media_type="text/plain",
                )
            else:
                query = unquote(request_body.get("query"))
        elif "application/sparql-query" in request.headers["content-type"]:
            """
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-post-direct
            2.1.3 query via POST directly
            Protocol clients may send protocol requests via the HTTP POST method by including the query directly and
            unencoded as the HTTP request message body. When using this approach, clients must include the SPARQL query
            string, unencoded, and nothing else as the message body of the request. Clients must set the content type
            header of the HTTP request to application/sparql-query. Clients may include the optional default-graph-uri
            and named-graph-uri parameters as HTTP query string parameters in the request URI. Note that UTF-8 is the
            only valid charset here.
            """
            query = request.data.decode("utf-8")  # get the raw request
            if query is None:
                return Response(
                    "Your POST request to this SPARQL endpoint must contain the query in plain text in the "
                    "POST body if the Content-Type 'application/sparql-query' is used.",
                    status_code=400,
                )
        else:
            return Response(
                "Your POST request to this SPARQL endpoint must either the 'application/x-www-form-urlencoded' or"
                "'application/sparql-query' ContentType.",
                status_code=400,
            )

        try:
            if "CONSTRUCT" in query:
                format_mimetype = "text/turtle"
                return Response(
                    sparql_query2(
                        query, media_type=format_mimetype
                    ),
                    status_code=200,
                    media_type=format_mimetype,
                )
            else:
                return Response(
                    sparql_query2(query, format_mimetype),
                    status_code=200,
                )
        except ValueError as e:
            return Response(
                "Input error for query {}.\n\nError message: {}".format(query, str(e)),
                status_code=400,
                media_type="text/plain",
            )
        except ConnectionError as e:
            return Response(str(e), status_code=500)
    else:  # GET
        if request.args.get("query") is not None:
            # SPARQL GET request
            """
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-get
            2.1.1 query via GET
            Protocol clients may send protocol requests via the HTTP GET method. When using the GET method, clients must
            URL percent encode all parameters and include them as query parameter strings with the names given above.
            HTTP query string parameters must be separated with the ampersand (&) character. Clients may include the
            query string parameters in any order.
            The HTTP request MUST NOT include a message body.
            """
            query = request.args.get("query")
            if "CONSTRUCT" in query:
                acceptable_mimes = [x for x in RDF_MEDIATYPES]
                best = _best_match(acceptable_mimes, request.headers["accept"])
                query_result = sparql_query2(
                    query, media_type=best
                )
                file_ext = {
                    "text/turtle": "ttl",
                    "application/rdf+xml": "rdf",
                    "application/ld+json": "json",
                    "text/n3": "n3",
                    "application/n-triples": "nt",
                }
                return Response(
                    query_result,
                    status_code=200,
                    media_type=best,
                    headers={
                        "Content-Disposition": "attachment; filename=query_result.{}".format(
                            file_ext[best]
                        )
                    },
                )
            else:
                query_result = sparql_query2(query)
                return Response(
                    query_result, status_code=200, media_type="application/sparql-results+json"
                )
        else:
            # SPARQL Service Description
            """
            https://www.w3.org/TR/sparql11-service-description/#accessing
            SPARQL services made available via the SPARQL Protocol should return a service description document at the
            service endpoint when dereferenced using the HTTP GET operation without any query parameter strings
            provided. This service description must be made available in an RDF serialization, may be embedded in
            (X)HTML by way of RDFa, and should use content negotiation if available in other RDF representations.
            """

            acceptable_mimes = [x for x in RDF_MEDIATYPES] + ["text/html"]
            best = _best_match(acceptable_mimes, request.headers["accept"])
            if best == "text/html":
                # show the SPARQL query form
                return RedirectResponse(SparqlRenderer.instance_uri)
            elif best is not None:
                for item in RDF_MEDIATYPES:
                    if item == best:
                        rdf_format = best
                        return Response(
                            get_sparql_service_description(
                                rdf_fmt=rdf_format
                            ),
                            status_code=200,
                            media_type=best,
                        )

                return Response(
                    "Accept header must be one of " + ", ".join(acceptable_mimes) + ".",
                    status_code=400,
                )
            else:
                return Response(
                    "Accept header must be one of " + ", ".join(acceptable_mimes) + ".",
                    status_code=400,
                )