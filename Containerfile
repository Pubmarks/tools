FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ src/

RUN uv sync --locked --no-dev

EXPOSE 8080

CMD [".venv/bin/python", "-m", "tools.server"]
