from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import httpx
import uuid
import logging
from typing import Union
from config import *
# from pyldapi import renderer, renderer_container
from utils import utils

from starlette.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from routers import landing_page, conformance, collections, sparql
from monitoring import logging_config
from middlewares.correlation_id_middleware import CorrelationIdMiddleware
from middlewares.logging_middleware import LoggingMiddleware
from api import landing_page as landing_page_api
from api import collection as collection_api
from api import collections as collections_api
from api import feature as feature_api
from api import features as features_api

api = FastAPI(
    docs_url="/docs",
    version="1.0",
    title=API_TITLE,
    description=f"Open API Documentation for this {API_TITLE}",
)

LOGGING = True # toggles logging, set to false for proper error messages

if LOGGING:
    logging_config.configure_logging(level='INFO', service='ogc-api', instance=str(uuid.uuid4()))
    api.add_middleware(LoggingMiddleware)

api.add_middleware(CorrelationIdMiddleware)

api.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["x-apigateway-header", "Content-Type", "X-Amz-Date"])


@api.get("/spec", summary="API Description Page")
def spec():
    openapi_json = api.openapi()
    return JSONResponse(openapi_json)


@api.get("/reload-data", summary="Endpoint to reload data from graph")
def reload():
    try:
        utils.get_graph()
        configure_data()
        return JSONResponse(content="Data reloaded.", status_code=200)
    except Exception as e:
        return HTTPException(content=e, status_code=500)


def configure():
    # Load data
    logging.info("Loading graph")
    utils.get_graph()
    logging.info("Graph loaded")
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
    landing_page_api.prefixes = utils.prefixes
    collection_api.prefixes = utils.prefixes
    collections_api.prefixes = utils.prefixes
    feature_api.prefixes = utils.prefixes
    features_api.prefixes = utils.prefixes
    conformance.prefixes = utils.prefixes
    collections.prefixes = utils.prefixes
    # renderer.MEDIATYPE_NAMES = MEDIATYPE_NAMES
    # renderer_container.MEDIATYPE_NAMES = MEDIATYPE_NAMES


def configure_routing():
    api.mount("/static", StaticFiles(directory="static"), name="static")
    api.include_router(landing_page.router)
    api.include_router(conformance.router)
    api.include_router(collections.router)
    api.include_router(sparql.router)
    set_theme()

def set_theme():
    """
    Gets theming files to disk using URLs from env variables
    
    Theming files are currently stored in S3, with a folder
    for each theme, i.e. ga-theme/, abs-theme/, etc.
    """
    get_theming_file(HEADER, "header")
    get_theming_file(FOOTER, "footer")
    get_theming_file(STYLESHEET, "stylesheet", is_html=False)

def get_theming_file(env_var: Union[str, None], var_name: str, is_html: bool = True) -> None:
    """Attempts to get theming file, defaults to template file if unsuccessful"""
    default_template = f"templates/{var_name}_template.html" if is_html else ""
    new_file = f"templates/{var_name}.html" if is_html else f"static/css/{var_name}.css"
    if env_var:
        try:
            r = httpx.get(env_var)
            if not 200 <= r.status_code < 300:
                logging.error(f"Broken {var_name} URL")
                raise Exception(f"Broken {var_name} URL")
            with open(new_file, "w") as f:
                f.write(r.text)
        except:
            if is_html:
                with open(default_template) as f:
                    base_content = f.read()
                with open(new_file, "w") as f:
                    f.write(base_content)
            else:
                with open(new_file, "w") as f:
                    f.write("")
    else:
        if is_html:
            with open(default_template) as f:
                base_content = f.read()
            with open(new_file, "w") as f:
                f.write(base_content)
        else:
            with open(new_file, "w") as f:
                f.write("")

if __name__ == "__main__":
    logging.info("Running main function")
    configure()
    if LOGGING:
        uvicorn.run(
            api,
            port=PORT,
            host=HOST,
            log_config=logging_config.configure_logging(
                service="Uvicorn"
            )
        )
    else:
        uvicorn.run(
            api,
            port=PORT,
            host=HOST
        )
else:
    logging.info("Running uvicorn function")
    configure()
