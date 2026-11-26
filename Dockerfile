# One image for both the web app and the worker (compose picks the command).
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project

COPY src ./src
COPY deploy ./deploy
RUN uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --system --uid 1000 app
USER app

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "simpy_aws_demo.app:create_app()"]
