"""
MerchAudit API — FastAPI backend.

Run with:
    uvicorn backend.main:app --reload

Loads the trained anomaly model ONCE at startup (inference-only in request
handlers — see backend/ml/train_model.py for the separate training job).
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database
from .routers import audits, auth, merchants, reports
from merchaudit.anomaly_engine import AnomalyEngine

MODEL_DIR = os.getenv("MODEL_DIR", "models/current")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    try:
        app.state.anomaly_engine = AnomalyEngine.load(MODEL_DIR)
        print(f"Loaded anomaly model from {MODEL_DIR} (version={app.state.anomaly_engine.model_version})")
    except FileNotFoundError:
        app.state.anomaly_engine = None
        print(
            f"WARNING: no trained model found at {MODEL_DIR}. "
            f"Run `python backend/ml/train_model.py` before using /audit endpoints."
        )
    yield


app = FastAPI(
    title="MerchAudit API",
    description="Two-layer merchant risk auditing: business rules + Isolation Forest anomaly detection.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_ORIGINS", "http://localhost:8501").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(merchants.router)
app.include_router(audits.router)
app.include_router(reports.router)


@app.get("/health")
def health():
    engine = app.state.anomaly_engine
    return {
        "status": "ok",
        "model_loaded": engine is not None,
        "model_version": engine.model_version if engine else None,
    }
