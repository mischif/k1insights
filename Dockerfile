# syntax=docker/dockerfile:1

FROM python:3.8-slim-bullseye AS base

RUN apt-get update && apt-get -y upgrade && apt-get -y install git

FROM base AS compile

WORKDIR /app

RUN pip install -U build

COPY .git/ ./.git/
COPY *.md pyproject.toml supervisord.conf ./
COPY src/ ./src/

RUN python -m build -w

FROM base AS deploy

VOLUME ["/data"]
EXPOSE 5000
RUN useradd -m fakeuser && pip install gunicorn supervisor
COPY --from=compile /app/dist/*.whl /app/supervisord.conf ./
RUN pip install *.whl
ENTRYPOINT (k1-create-db ${K1_DATA_DB} || true) \
			&& chown -R fakeuser:fakeuser /data \
			&& k1-start-all
