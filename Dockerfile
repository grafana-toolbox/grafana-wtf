# -----
# Build
# -----
FROM python:3.13-bookworm AS build

# For more verbose output, use:
# export BUILDKIT_PROGRESS=plain

# Configure operating system
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=linux

# Configure build environment
ENV PIP_ROOT_USER_ACTION=ignore
ENV UV_COMPILE_BYTECODE=true
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=never

# Provide package sources
COPY . /src

# Install package and dependencies
RUN \
    --mount=type=cache,id=pip,target=/root/.cache/pip \
    --mount=type=cache,id=uv,target=/root/.cache/uv \
    true \
    && pip install uv \
    && uv venv --no-project --relocatable /app \
    && uv pip install --directory=/app /src

# Install optional software
RUN wget --quiet --output-document=/tmp/jq "https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-linux-amd64"
RUN chmod +x /tmp/jq


# ------------
# Distribution
# ------------
FROM python:3.13-slim-bookworm
COPY --from=build /app /opt/grafana-wtf
COPY --from=build /tmp/jq /usr/local/bin/jq
ENV PATH="$PATH:/opt/grafana-wtf/bin"
