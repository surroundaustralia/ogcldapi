from fastapi import Response
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pyldapi import Renderer

from api.link import *
from api.profiles import *
from config import *


templates = Jinja2Templates(directory="templates")


class ConformanceRenderer(Renderer):
    def __init__(self, request, conformance_classes):

        self.conformance_classes = conformance_classes

        super().__init__(
            request,
            LANDING_PAGE_URL + "/conformance",
            {"oai": profile_openapi},
            "oai"
        )

        self.ALLOWED_PARAMS = ["_profile", "_view", "_mediatype", "_format", "version"]

    def render(self):
        for v in self.request.query_params.items():
            if v[0] not in self.ALLOWED_PARAMS:
                return Response(
                    "The parameter {} you supplied is not allowed".format(v[0]),
                    status=400,
                )

        # try returning alt profile
        template_context = {
            "api_title": f"Conformance - {API_TITLE}"
        }
        response = super().render(
            additional_alt_template_context=template_context
        )
        if response is not None:
            return response
        elif self.profile == "oai":
            if self.mediatype in [
                "application/json",
                "application/vnd.oai.openapi+json;version=3.0",
                "application/geo+json",
            ]:
                return self._render_oai_json()
            else:
                return self._render_oai_html()

    def _render_oai_json(self):
        page_json = {"conformsTo": self.conformance_classes}

        return JSONResponse(
            page_json,
            media_type=str(MediaType.JSON.value),
            headers=self.headers,
        )

    def _render_oai_html(self):
        _template_context = {
            "uri": LANDING_PAGE_URL + "/conformance",
            "conformance_classes": self.conformance_classes,
            "request": self.request,
            "api_title": f"Conformance - {API_TITLE}"
        }

        return templates.TemplateResponse(
            name="conformance.html", context=_template_context, headers=self.headers
        )
