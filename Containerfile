FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN uv sync --no-dev

EXPOSE 8080

CMD ["uv", "run", "python", "-m", "tools.server"]
