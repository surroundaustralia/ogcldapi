from enum import Enum


class RelType(Enum):
    SELF = "self"
    SERVICE_DESC = "service-desc"
    SERVICE_DOC = "service-doc"
    CONFORMANCE = "conformance"
    DATA = "data"
    ITEMS = "items"


class MediaType(Enum):
    HTML = "text/html"
    JSON = "application/json"
    JSON_LD = "application/ld+json"
    GEOJSON = "application/geo+json"
    TURTLE = "text/turtle"
    OPEN_API_3 = "application/vnd.oai.openapi+json;version=3.0"


class HrefLang(Enum):
    EN = "en"


class Link(object):
    def __init__(
        self,
        href: str,
        rel: RelType = None,
        type: MediaType = None,
        hreflang: HrefLang = None,
        title: str = None,
        length: int = None,
    ):
        self.href = href
        self.rel = rel
        self.type = type
        self.hreflang = hreflang
        self.title = title
        self.length = length

    def render_as_http_header(self):
        http = "<{}>".format(self.href)
        if self.rel is not None:
            http += '; rel="{}"'.format(self.rel.value)
        if self.type is not None:
            http += '; type="{}"'.format(self.type.value)
        if self.hreflang is not None:
            http += '; hreflang="{}"'.format(self.hreflang.value)
        if self.title is not None:
            http += '; title="{}"'.format(self.title)
        if self.length is not None:
            http += '; length="{}"'.format(self.length)

        return http

    def to_dict(self):
        return self.__dict__
