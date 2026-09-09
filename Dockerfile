FROM python:3.13.5-alpine3.22

WORKDIR /app
COPY requirements.txt ./

# Updates to newest packages,
RUN apk update \
    && apk upgrade --no-cache --available \
    && apk add --no-cache \
    && pip install --no-cache-dir -r requirements.txt \
    && mkdir ./config

COPY ./src/ ./

ENTRYPOINT ["python3", "ingestion.py"]
