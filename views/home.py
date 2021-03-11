import fastapi
from starlette.requests import Request
from starlette.templating import Jinja2Templates
from fastapi import APIRouter

templates = Jinja2Templates('templates')
router = APIRouter()

@router.get('/')
async def index(request: Request):
    return templates.TemplateResponse('api.html', {'request': request})
