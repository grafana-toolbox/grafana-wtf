FROM python:3.9-slim-bullseye

ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# Install prerequisites
RUN apt-get update
RUN apt-get --yes install jq

# Provide sources
COPY . /app

# Install package
WORKDIR /app
RUN pip install .
