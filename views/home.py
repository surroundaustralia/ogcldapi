from starlette.templating import Jinja2Templates
from fastapi import APIRouter, Header
from app.renderers import render, JSONRenderer, PlainTextRenderer, HTMLRenderer
from typing import Optional

templates = Jinja2Templates('templates')
router = APIRouter()

@router.get("/")
async def index(accept: Optional[str] = Header(default='text/plain')):
    data = 'test'
    return render(
        data, accept, status_code=200,
        renderers=[JSONRenderer, PlainTextRenderer, HTMLRenderer])
