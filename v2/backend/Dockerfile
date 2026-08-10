FROM ghcr.io/astral-sh/uv:0.11.19 AS uv

FROM python:3.13.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/domcek-venv \
    PATH="/opt/domcek-venv/bin:$PATH"

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY README.md alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY scripts ./scripts
RUN uv sync --locked --no-dev

RUN addgroup --system domcek && adduser --system --ingroup domcek domcek \
    && mkdir -p /var/lib/domcek/media \
    && chown -R domcek:domcek /app /var/lib/domcek
USER domcek

CMD ["domcek-api"]
