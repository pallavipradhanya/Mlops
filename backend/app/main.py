from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.database.db import init_db
from app.retraining import scheduler
from app.services import mlflow_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        mlflow_service.setup()
    except Exception as exc:  # MLflow server may still be starting; endpoints retry on demand
        print(f"[warn] MLflow not ready yet: {exc}")
    if settings.enable_scheduler:
        scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="MLOps360 API", version="1.0.0", lifespan=lifespan,
              description="Local end-to-end MLOps: datasets, training, registry, predictions, drift, retraining.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/")
def root():
    return {"name": "MLOps360", "docs": "/docs", "health": "/api/health"}
