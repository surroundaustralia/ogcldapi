from typing import Optional

from fastapi import APIRouter, Header
from starlette.templating import Jinja2Templates

from app.renderers import render, HTMLRenderer

templates = Jinja2Templates('templates')
router = APIRouter()

@router.get("/")
async def index(accept: Optional[str] = Header(default='text/plain')):
    data = None
    return render(
        data, accept, status_code=200,
        # renderers=[JSONRenderer, PlainTextRenderer, HTMLRenderer])
        renderers=[HTMLRenderer])
