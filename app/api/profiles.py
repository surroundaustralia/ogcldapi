from pyldapi.profile import Profile
from pyldapi.fastapi_framework import Renderer


profile_openapi = Profile(
    "http://www.opengis.net/spec/ogcapi-features-1/1.0/req/oas30",
    label="OpenAPI 3.0",
    comment="The OpenAPI Specification (OAS) defines a standard, language-agnostic interface to RESTful APIs which "
            "allows both humans and computers to discover and understand the capabilities of the service without "
            "access to source code, documentation, or through network traffic inspection.",
    mediatypes=["text/html", "application/geo+json", "application/json", "application/vnd.oai.openapi+json;version=3.0"],
    default_mediatype="application/geo+json",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_dcat = Profile(
    "https://www.w3.org/TR/vocab-dcat/",
    label="DCAT",
    comment="Dataset Catalogue Vocabulary (DCAT) is a W3C-authored RDF vocabulary designed to "
    "facilitate interoperability between data catalogs "
    "published on the Web.",
    mediatypes=["text/html", "application/json"] + Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_geosparql = Profile(
    "http://www.opengis.net/ont/geosparql",
    label="GeoSPARQL",
    comment="An RDF/OWL vocabulary for representing spatial information",
    mediatypes=Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/turtle",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)
