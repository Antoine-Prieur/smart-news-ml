FROM python:3.13-slim as builder

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

ENV POETRY_VENV_IN_PROJECT=1
ENV POETRY_CACHE_DIR=/opt/poetry-cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR

FROM python:3.13-slim as runtime

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

RUN mkdir -p /app/data/weights && chown -R appuser:appuser /app/data

COPY src/ ./src/

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

RUN chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "src.main"]
