import fastapi
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.landing_page import LandingPageRenderer

router = fastapi.APIRouter()

templates = Jinja2Templates(directory="templates")

# @router.get("/")
# def landing_page():
#     try:
#         return LandingPageRenderer(request).render()
#     except Exception as e:
#         logging.debug(e)
#         return Response(
#             "ERROR: " + str(e),
#             status=500,
#             mimetype="text/plain"
#         )


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # return templates.TemplateResponse("page.html", {"request": request,
    #                                                 "collections_route": "/collections",
    #                                                 "conformance_route": "conformance"})
    # print("request", request.json())
    # test = await request.body()
    # print(test)
    # body = await request.body()
    # print(body)
    # return await request.json()
    LandingPageRenderer(request).render()
