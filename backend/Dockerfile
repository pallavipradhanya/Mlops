# One image runs both the API and the MLflow tracking server (keeps disk usage down on a laptop).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MLOPS_HOME=/workspace

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/backend
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/app ./app

# Writable locations (named volumes inherit this ownership on first use)
RUN useradd --create-home app \
    && mkdir -p /workspace/data/uploads /workspace/artifacts /workspace/models /workspace/reports /workspace/mlruns /mlflow \
    && chown -R app:app /workspace /mlflow /srv/backend
USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
