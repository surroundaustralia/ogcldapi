import os
from rdflib import Namespace

__version__ = "1.2"
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
GEOX = Namespace("https://linked.data.gov.au/def/geox#")
OGCAPI = Namespace("https://data.surroundaustralia.com/def/ogcldapi/")

DEBUG = os.getenv("DEBUG", True)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = os.getenv("PORT", 9000)

APP_DIR = os.getenv("APP_DIR", os.path.dirname(os.path.realpath(__file__)))
TEMPLATES_DIR = os.getenv("TEMPLATES_DIR", os.path.join(APP_DIR, "view", "templates"))
STATIC_DIR = os.getenv("STATIC_DIR", os.path.join(APP_DIR, "view", "style"))
LOGFILE = os.getenv("LOGFILE", os.path.join(APP_DIR, "ogcldapi.log"))

CACHE_FILE = os.getenv("CACHE_DIR", os.path.join(APP_DIR, "cache", "DATA.pickle"))
CACHE_HOURS = os.getenv("CACHE_HOURS", 1)
LOCAL_URIS = os.getenv("LOCAL_URIS", True)
VERSION = os.getenv("VERSION", __version__)
API_TITLE = os.getenv("API_TITLE", "OGC LD API")
LANDING_PAGE_URL = os.getenv("LANDING_PAGE_URL", f"http://localhost:{PORT}")
DATASET_URI = os.getenv("DATASET_URI", "https://linked.data.gov.au/dataset/floods")
SPARQL_ENDPOINT = os.getenv(
    "SPARQL_ENDPOINT", "http://fuseki.surroundaustralia.com/floods"
)
TEST_GRAPH = os.getenv("TEST_GRAPH", None)

MEDIATYPE_NAMES = {
    "text/html": "HTML",
    "application/json": "JSON",
    "application/geo+json": "GeoJSON",
    "text/turtle": "Turtle",
    "application/rdf+xml": "RDX/XML",
    "application/ld+json": "JSON-LD",
    "text/n3": "Notation-3",
    "application/n-triples": "N-Triples",
}
