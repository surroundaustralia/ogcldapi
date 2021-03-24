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

    render_content = LandingPageRenderer(request).render()
    return render_content
