from fastapi import FastAPI
import uvicorn
from config import *

from starlette.staticfiles import StaticFiles
from routers import landing_page, conformance


app = FastAPI(docs_url='/docs',
              version='1.0',
              title='OGC LD API',
              description=f"Open API Documentation for this {API_TITLE}")


def configure():
    configure_routing()


def configure_routing():
    app.mount('/static', StaticFiles(directory='static'), name='static')
    app.include_router(landing_page.router)
    app.include_router(conformance.router)


if __name__ == '__main__':
    configure()
    uvicorn.run(app, port=PORT, host=HOST)
else:
    configure()
