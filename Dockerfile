FROM python:3.13-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=linux

# Install prerequisites
RUN apt-get update
RUN apt-get --yes install jq

# Provide sources
COPY . /src

# Install package
ENV UV_SYSTEM_PYTHON=true
RUN \
    true \
    && pip install uv \
    && uv pip install /src \
    && uv pip uninstall uv
