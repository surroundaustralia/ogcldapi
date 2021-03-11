from fastapi import FastAPI
import uvicorn
import logging
from views import home
from starlette.staticfiles import StaticFiles

logging.basicConfig(
    # TODO logfile location
    filename='log.txt',
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
    format="%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s",
)

app = FastAPI()


def configure():
    app.mount('/static', StaticFiles(directory='static'), name='static')
    app.include_router(home.router)


if __name__ == '__main__':
    configure()
    uvicorn.run(app, port=8000, host='127.0.0.1')
else:
    configure()
