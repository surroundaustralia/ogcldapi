FROM tiangolo/uvicorn-gunicorn-fastapi
# workdir is set in the base image to 'app' so copy requirements here
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY ./ /app/
