from fastapi import FastAPI
import uvicorn
from config import *
from utils import utils

from starlette.staticfiles import StaticFiles
from routers import landing_page, conformance, collections
from api import landing_page as landing_page_api
from api import collection as collection_api
from api import collections as collections_api
from api import feature as feature_api
from api import features as features_api

app = FastAPI(docs_url='/docs',
              version='1.0',
              title='OGC LD API',
              description=f"Open API Documentation for this {API_TITLE}")


def configure():
    # Load data
    utils.get_graph()
    configure_routing()
    configure_data()


def configure_data():
    landing_page_api.g = utils.g
    collection_api.g = utils.g
    collections_api.g = utils.g
    feature_api.g = utils.g
    features_api.g = utils.g
    conformance.g = utils.g
    collections.g = utils.g


def configure_routing():
    app.mount('/static', StaticFiles(directory='static'), name='static')
    app.include_router(landing_page.router)
    app.include_router(conformance.router)
    app.include_router(collections.router)


if __name__ == '__main__':
    configure()
    uvicorn.run(app, port=PORT, host=HOST)
else:
    configure()
