from views.link import *
from flask import Response, render_template
from views.profiles import *
from config import *
import json


class ConformanceRenderer(Renderer):
    def __init__(
            self,
            request,
            conformance_classes):

        self.conformance_classes = conformance_classes

        super().__init__(request, LANDING_PAGE_URL + "/conformance", {"oai": profile_openapi}, "oai")

        self.ALLOWED_PARAMS = ["_profile", "_view", "_mediatype", "_format"]

    def render(self):
        for v in self.request.query_params.items():
            if v[0] not in self.ALLOWED_PARAMS:
                return Response("The parameter {} you supplied is not allowed".format(v[0]), status=400)

        # try returning alt profile
        response = super().render()
        if response is not None:
            return response
        elif self.profile == "oai":
            if self.mediatype in ["application/json", "application/vnd.oai.openapi+json;version=3.0", "application/geo+json"]:
                return self._render_oai_json()
            else:
                return self._render_oai_html()

    def _render_oai_json(self):
        page_json = {
            "conformsTo": self.conformance_classes
        }

        return Response(
            json.dumps(page_json),
            mimetype=str(MediaType.JSON.value),
            headers=self.headers,
        )

    def _render_oai_html(self):
        _template_context = {
            "uri": LANDING_PAGE_URL + "/conformance",
            "conformance_classes": self.conformance_classes
        }

        return Response(
            render_template("conformance.html", **_template_context),
            headers=self.headers,
        )

