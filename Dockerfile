FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

ENV APP_MODULE="app:api"

COPY ./app /app
RUN pip install -r /app/requirements.txt

#docker build -t ogc-api . -f Dockerfile
#docker run -p 8000:80 -d -it --name ogc-api --restart unless-stopped ogc-api
