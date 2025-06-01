# syntax=docker/dockerfile:1

FROM ghcr.io/linuxserver/baseimage-alpine:3.21

# set version label
ARG BUILD_DATE
ARG VERSION
LABEL build_version="Linuxserver.io version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="hackerman"

COPY . /app

RUN \
  echo "**** install dependencies ****" && \
  apk add --no-cache \
    nodejs \
    npm \
    python3 \
    py3-pip \
    py3-virtualenv && \
  virtualenv /lsiopy && \
  cd /app && \
  pip install -r requirements.txt && \
  cd /app/frontend && \
  npm install && \
  npm run build && \
  echo "**** clean up ****" && \
  rm -rf \
    /tmp/* \
    /app/frontend/node_modules

# add local files
COPY /root /
