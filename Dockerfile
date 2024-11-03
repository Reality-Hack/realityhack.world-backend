FROM python:3.12.1-alpine3.19

RUN apk update
RUN apk add alpine-sdk libressl-dev libffi-dev

RUN mkdir -p /home
WORKDIR /home

ENV DJANGO_SECRET_KEY=123456
ENV DEBUG=true
ENV DEPLOYED=false
ENV FRONTEND_DOMAIN=http://0.0.0.0:3000
ENV KEYCLOAK_SERVER_URL=http://0.0.0.0:8080/
ENV KEYCLOAK_REALM=master
ENV KEYCLOAK_CLIENT_ID=test
ENV KEYCLOAK_CLIENT_SECRET_KEY=123456
ENV BACKEND_DOMAIN=http://0.0.0.0:8000
ENV EMAIL_HOST=
ENV EMAIL_PORT=
ENV EMAIL_HOST_USER=
ENV EMAIL_HOST_PASSWORD=
ENV EMAIL_USE_SSL=

COPY pyproject.toml poetry.lock /home/
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-root --no-interaction

COPY . /home
