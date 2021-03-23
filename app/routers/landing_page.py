from typing import Optional

import fastapi
from fastapi import Request
from fastapi.templating import Jinja2Templates

from api.landing_page import LandingPageRenderer

router = fastapi.APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def home(request: Request,
               _view: Optional[str] = None,
               _profile: Optional[str] = None,
               _format: Optional[str] = None,
               _mediatype: Optional[str] = None):

    print("A", request.query_params)
    print("B", request.query_params.values())
    print("C", request.query_params.get('_view'))
    print(type(LandingPageRenderer(request).render()))
    render_content = LandingPageRenderer(request).render()
    return render_content
