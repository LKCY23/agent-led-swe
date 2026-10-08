FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.8.18 && uv venv /opt/testenv
COPY requirements.txt /tmp/requirements.txt
RUN uv pip install --python /opt/testenv/bin/python --require-hashes -r /tmp/requirements.txt && rm -rf /root/.cache
ENV PATH="/opt/testenv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_NO_CACHE=1
