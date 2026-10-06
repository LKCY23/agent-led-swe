FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential libsndfile1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.8.18 && uv venv /opt/testenv
COPY requirements.in /tmp/requirements.in
RUN apt-get update && apt-get install -y --no-install-recommends pkg-config libhdf5-dev libnetcdf-dev && rm -rf /var/lib/apt/lists/*
RUN --mount=type=cache,target=/root/.cache/uv uv pip install --python /opt/testenv/bin/python --exclude-newer 2024-07-17 -r /tmp/requirements.in
ENV PATH="/opt/testenv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_NO_CACHE=1
ENV LITELLM_LOCAL_MODEL_COST_MAP=True
