from typing import List
from views.link import *
from flask import Response, render_template
from rdflib import URIRef, Literal
from rdflib.namespace import DCAT, DCTERMS, RDF
from views.profiles import *
from config import *
import json
import markdown
import logging


class LandingPage:
    def __init__(
            self,
            other_links: List[Link] = None,
    ):
        logging.debug("LandingPage()")
        self.uri = LANDING_PAGE_URL

        # make dummy Landing Page data
        g = get_graph()
        self.description = None
        for s in g.subjects(predicate=RDF.type, object=DCAT.Dataset):
            for p, o in g.predicate_objects(subject=s):
                if p == DCTERMS.title:
                    self.title = str(o)
                elif p == DCTERMS.description:
                    self.description = markdown.markdown(o)
        logging.debug("LandingPage() RDF loops")

        # make links
        self.links = [
            Link(
                LANDING_PAGE_URL,
                rel=RelType.SELF,
                type=MediaType.JSON,
                hreflang=HrefLang.EN,
                title="This document"
            ),
            Link(
                LANDING_PAGE_URL + "/spec",
                rel=RelType.SERVICE_DESC,
                type=MediaType.OPEN_API_3,
                hreflang=HrefLang.EN,
                title="API definition"
            ),
            Link(
                LANDING_PAGE_URL + "/doc/",
                rel=RelType.SERVICE_DOC,
                type=MediaType.HTML,
                hreflang=HrefLang.EN,
                title="API documentation"
            ),
            Link(
                LANDING_PAGE_URL + "/conformance",
                rel=RelType.CONFORMANCE,
                type=MediaType.JSON,
                hreflang=HrefLang.EN,
                title="OGC API conformance classes implemented by this server"
            ),
            Link(
                LANDING_PAGE_URL + "/collections",
                rel=RelType.DATA,
                type=MediaType.JSON,
                hreflang=HrefLang.EN,
                title="Information about the feature collections"
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

        super().__init__(request, self.landing_page.uri, {"oai": profile_openapi, "dcat": profile_dcat}, "oai")

        # add OGC API Link headers to pyLDAPI Link headers
        self.headers["Link"] = self.headers["Link"] + ", ".join([link.render_as_http_header() for link in self.landing_page.links])

        self.ALLOWED_PARAMS = ["_profile", "_view", "_mediatype", "_format"]

    def render(self):
        logging.debug("LandingPageRenderer.render()")
        for v in self.request.values.items():
            if v[0] not in self.ALLOWED_PARAMS:
                return Response("The parameter {} you supplied is not allowed".format(v[0]), status=400)

        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "oai":
            if self.mediatype == "application/json":
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
            l = {
                "href": link.href
            }
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

        return Response(
            json.dumps(page_json),
            mimetype=str(MediaType.JSON.value),
            headers=self.headers,
        )

    def _render_oai_html(self):
        _template_context = {
            "uri": self.landing_page.uri,
            "title": self.landing_page.title,
            "landing_page": self.landing_page
        }

        return Response(
            render_template("landing_page_oai.html", **_template_context),
            headers=self.headers,
        )

    def _render_dcat_rdf(self):
        g = Graph()
        g.bind("dcat", DCAT)
        g.add((
            URIRef(self.landing_page.uri),
            RDF.type,
            DCAT.Dataset
        ))
        g.add((
            URIRef(self.landing_page.uri),
            DCTERMS.title,
            Literal(self.landing_page.title)
        ))
        g.add((
            URIRef(self.landing_page.uri),
            DCTERMS.description,
            Literal(self.landing_page.description)
        ))

        # serialise in the appropriate RDF format
        if self.mediatype in ["application/rdf+json", "application/json"]:
            return Response(g.serialize(format="json-ld"), mimetype=self.mediatype)
        else:
            return Response(g.serialize(format=self.mediatype), mimetype=self.mediatype)

    def _render_dcat_html(self):
        _template_context = {
            "uri": self.dataset.uri,
            "label": self.dataset.label,
            "description": markdown.markdown(self.dataset.description),
            "parts": self.dataset.parts,
            "distributions": self.dataset.distributions,
        }

        return Response(
            render_template("dataset.html", **_template_context),
            headers=self.headers,
        )
