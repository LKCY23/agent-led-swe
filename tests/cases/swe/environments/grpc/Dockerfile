FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.8.18
COPY requirements.txt /tmp/requirements.txt
RUN uv pip install --system --require-hashes -r /tmp/requirements.txt && rm -rf /root/.cache
RUN mkdir /app && ln -s /app /testbed
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_NO_CACHE=1
