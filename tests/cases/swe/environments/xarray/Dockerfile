FROM agent-led-swe-xarray:20261006-v2
RUN uv pip freeze --python /opt/testenv/bin/python > /tmp/constraints.txt && uv pip install --python /opt/testenv/bin/python --exclude-newer 2024-07-17 -c /tmp/constraints.txt numexpr pint array-api-strict
