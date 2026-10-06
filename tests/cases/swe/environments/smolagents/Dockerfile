FROM agent-led-swe-smolagents:20261006-v1
RUN --mount=type=cache,target=/root/.cache/uv uv pip install --python /opt/testenv/bin/python --exclude-newer 2025-06-10 scipy scikit-learn
RUN uv pip freeze --python /opt/testenv/bin/python > /tmp/constraints.txt && uv pip install --python /opt/testenv/bin/python -c /tmp/constraints.txt "mlx[cpu]==0.30.0" mlx-lm==0.25.2
RUN python -c "import scipy, sklearn, mlx_lm"
