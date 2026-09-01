from fastapi import FastAPI
from app.database import Base, engine
from app.models import orm  # noqa: F401 - registers models
from app.routers import assets, telemetry, maintenance, depreciation, feeds, forecasting

# Create tables if they don't exist (Docker init.sql also does this;
# this makes the app work even against a fresh empty DB).
# Wrapped so importing the app never fails when the DB isn't reachable
# (e.g. during tests, which override the DB with in-memory SQLite).
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

app = FastAPI(
    title="AssetPulse API",
    description="Asset Tracking & Management System - IMPACT pSiddhi 3.0",
    version="0.1.0",
)

app.include_router(assets.router)
app.include_router(telemetry.router)
app.include_router(maintenance.router)
app.include_router(depreciation.router)
app.include_router(feeds.router)
app.include_router(forecasting.router)


@app.get("/")
def root():
    return {"service": "AssetPulse", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}
