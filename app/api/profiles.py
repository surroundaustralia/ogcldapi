from pyldapi import Profile, RDF_MEDIATYPES


profile_openapi = Profile(
    "http://www.opengis.net/spec/ogcapi-features-1/1.0/req/oas30",
    label="OpenAPI 3.0",
    comment="The OpenAPI Specification (OAS) defines a standard, language-agnostic interface to RESTful APIs which "
    "allows both humans and computers to discover and understand the capabilities of the service without "
    "access to source code, documentation, or through network traffic inspection.",
    mediatypes=[
        "text/html",
        "application/geo+json",
        "application/json",
        "application/vnd.oai.openapi+json;version=3.0",
    ],
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
    mediatypes=["text/html", "application/json"] + RDF_MEDIATYPES,
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_geosparql = Profile(
    "http://www.opengis.net/ont/geosparql",
    label="GeoSPARQL",
    comment="An RDF/OWL vocabulary for representing spatial information",
    mediatypes=RDF_MEDIATYPES,
    default_mediatype="text/turtle",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_mem = Profile(
    "https://w3id.org/profile/mem",
    label="Members Profile",
    comment="A very basic RDF data model-only profile that lists the sub-items (members) of collections (rdf:Bag)",
    mediatypes=["text/html"],
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)