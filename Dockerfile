FROM python:3.13-slim-bookworm

# Configure operating system
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=linux

# Provide package sources
COPY . /src

# Install package and dependencies
ENV UV_COMPILE_BYTECODE=true
ENV UV_NO_CACHE=true
ENV UV_PYTHON_DOWNLOADS=never
ENV UV_SYSTEM_PYTHON=true
RUN \
    true \
    # Install package.
    && pip install uv \
    && uv pip install /src \
    && uv pip uninstall uv \
    # Install `jq`.
    && apt-get update \
    && apt-get install --no-install-recommends --no-install-suggests --yes jq \
    # Tear down.
    && apt-get autoremove --yes \
    && apt-get autoclean --yes \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache \
    && rm -rf /src \
    && rm -rf /tmp/*
