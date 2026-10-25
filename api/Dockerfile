FROM python:3.14.4-slim

WORKDIR /api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/api/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-group training --no-install-project

COPY . .
RUN uv sync --frozen --no-dev --no-group training

EXPOSE 8000

CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]