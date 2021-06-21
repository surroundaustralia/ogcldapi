from api.link import *

from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from pyldapi.fastapi_framework import Renderer
from api.profiles import *
from config import *


templates = Jinja2Templates(directory="templates")


class ApiDescRenderer(Renderer):
    def __init__(
            self,
            request,
            paths
    ):
        """
        "/search/find_dggs_by_geojson": {
            "parameters": [
                {
                    "name": "resolution",
                    "in": "query",
                    "type": "integer",
                    "required": true,
                    "description": "DGGS Resolution 4 to 12 (high resolution settings and big areas can take a much longer time)",
                    "default": 10,
                    "enum": [
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12
                    ],
                    "collectionFormat": "multi"
                },
                {
                    "name": "dggs_as_polygon",
                    "in": "query",
                    "type": "string",
                    "description": "Return geojson with DGGS cells as polygon features when set True (default True), return original geojson object when set False",
                    "default": "True",
                    "enum": [
                        "False",
                        "True"
                    ],
                    "collectionFormat": "multi"
                },
                {
                    "name": "keep_properties",
                    "in": "query",
                    "type": "string",
                    "description": "Keep the geojson features' properties at the returned geojson when set True (default True)",
                    "default": "True",
                    "enum": [
                        "False",
                        "True"
                    ],
                    "collectionFormat": "multi"
                },
                {
                    "name": "payload",
                    "required": true,
                    "in": "body",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "geojson": {
                                "type": "string"
                            }
                        }
                    }
                }
            ],
            "post": {
                "responses": {
                    "200": {
                        "description": "Success"
                    }
                },
                "operationId": "post_find_dggs_by_geojson",
                "tags": [
                    "search"
                ]
            }
        },
        """
        self.paths = {}
        for rule in paths.iter_rules():
            self.paths[LANDING_PAGE_URL + "/" + rule.endpoint] = {
                "get": {
                    "description": "Returns all pets from the system that the user has access to",
                    "operationId": "findPets",
                    "produces": [
                        "application/json",
                        "application/xml",
                        "text/xml",
                        "text/html"
                    ],
                },
                "parameters": [
                    # {
                    #     "name": "keep_properties",
                    #     "in": "query",
                    #     "type": "string",
                    #     "description": "Keep the geojson features' properties at the returned geojson when set True (default True)",
                    #     "default": "True",
                    #     "enum": [
                    #         "False",
                    #         "True"
                    #     ],
                    #     "collectionFormat": "multi"
                    # },
                ]
            }

        super().__init__(request, LANDING_PAGE_URL + "/api", {"oai": profile_openapi}, "oai")

    def render(self):
        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "oai":
            if self.mediatype == "application/json" or self.mediatype == "application/vnd.oai.openapi+json;version=3.0":
                return self._render_oai_json()
            else:
                return self._render_oai_html()

    def _render_oai_json(self):
        """
        {
            "swagger": "2.0",
            "basePath": "/api",
            "paths": {
                ...
            },
            "info": {
                "title": "DGGS Engine",
                "version": "0.1"
            },
            "produces": [
                "application/json"
            ],
            "consumes": [
                "application/json"
            ],
            "tags": [
                {
                    "name": "search",
                    "description": "Search from DGGS Engine"
                }
            ],
            "responses": {
                "ParseError": {
                    "description": "When a mask can't be parsed"
                },
                "MaskError": {
                    "description": "When any error occurs on mask"
                }
            }
        }
        """
        page_json = {
            "swagger": "2.0",
            "basePath": LANDING_PAGE_URL + "/api",
            "info": {
                "title": API_TITLE,
                "version": VERSION
            },
            "paths": self.paths,
        }

        return JSONResponse(
            page_json,
            media_type=str(MediaType.OPEN_API_3.value),
            headers=self.headers,
        )

    def _render_oai_html(self):
        _template_context = {
            "uri": LANDING_PAGE_URL + "/api",
            "api_title": f"API Description - {API_TITLE}"
        }

        return templates.TemplateResponse(name="api.html",
                                          context=_template_context,
                                          headers=self.headers)
