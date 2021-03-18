from fastapi import FastAPI
import uvicorn
# from views import home, collections
from starlette.staticfiles import StaticFiles
from routers import landing_page


app = FastAPI()


def configure():
    configure_routing()


def configure_routing():
    app.mount('/static', StaticFiles(directory='static'), name='static')
    app.include_router(landing_page.router)
    # app.include_router(collections.router)


if __name__ == '__main__':
    configure()
    uvicorn.run(app, port=8000, host='127.0.0.1')
else:
    configure()
