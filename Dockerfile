# syntax=docker/dockerfile:1

FROM python:3.8-slim-bullseye AS base

RUN apt-get update && apt-get -y upgrade && apt-get -y install git

FROM base AS compile

WORKDIR /app

RUN pip install -U build

COPY .git/ ./.git/
COPY LICENSE.md pyproject.toml supervisord.conf ./
COPY src/ ./src/

RUN python -m build -w

FROM base AS deploy

EXPOSE 5000
VOLUME ["/data"]

RUN useradd --create-home fakeuser
WORKDIR /home/fakeuser
USER fakeuser

ENV PATH="/home/fakeuser/.local/bin:$PATH" K1_DATA_DB=/tmp/k1.db
RUN pip install gunicorn supervisor

COPY --from=compile /app/dist/*.whl /app/supervisord.conf ./
RUN pip install *.whl

RUN k1-create-db /tmp/k1.db

ENTRYPOINT ["k1-start-all"]
