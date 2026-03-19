ARG PLAYWRIGHT_VERSION=1.58.0
FROM mcr.microsoft.com/playwright/python:v${PLAYWRIGHT_VERSION}-noble

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY uv.lock pyproject.toml ./
RUN uv sync --frozen --no-install-project --extra de --extra mcp --extra web

COPY . ./
RUN for f in permaculture/locales/*/LC_MESSAGES/*.po; do \
        python3 scripts/msgfmt.py --output-file "${f%.po}.mo" "$f"; \
    done

ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0
RUN uv sync --frozen --no-editable --extra de --extra mcp --extra web

ENTRYPOINT ["uv", "run", "--no-sync"]
