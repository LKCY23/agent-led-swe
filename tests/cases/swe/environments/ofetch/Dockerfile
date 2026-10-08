ARG OFETCH_BASE
FROM ${OFETCH_BASE}
RUN apt-get update && apt-get install -y --no-install-recommends python3 git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Node resolves parent node_modules; keep image dependencies outside public snapshots.
RUN ln -s /opt/ofetch-deps/node_modules /node_modules \
    && chmod -R a+rwX /opt/pnpm-store /opt/ofetch-deps/node_modules
ENV PATH="/node_modules/.bin:$PATH"
WORKDIR /testbed
