"""FastAPI endpoint tests (proposal 5.2: 100% of endpoints tested).

Uses an in-memory SQLite DB so tests run without Docker/Postgres.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# in-memory SQLite shared across the test session
engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture
def sample_asset():
    return {
        "asset_id": "A-999", "name": "Test Laptop", "category": "Computing Hardware",
        "purchase_date": "2023-01-01", "purchase_price": 60000,
        "useful_life_yrs": 5, "depr_method": "straight_line", "is_iot_enabled": True,
    }


def test_root():
    assert client.get("/").json()["status"] == "ok"


def test_create_and_get_asset(sample_asset):
    r = client.post("/assets", json=sample_asset)
    assert r.status_code == 200
    r2 = client.get("/assets/A-999")
    assert r2.json()["name"] == "Test Laptop"


def test_duplicate_asset_rejected(sample_asset):
    client.post("/assets", json=sample_asset)
    r = client.post("/assets", json=sample_asset)
    assert r.status_code == 400


def test_telemetry_ingest_and_range_guard():
    client.post("/assets", json={
        "asset_id": "A-500", "name": "S", "category": "Server & Networking",
        "purchase_date": "2023-01-01", "purchase_price": 100000, "is_iot_enabled": True,
    })
    ok = client.post("/telemetry", json={"asset_id": "A-500", "temperature_c": 55, "utilisation_pct": 40})
    assert ok.status_code == 200
    bad = client.post("/telemetry", json={"asset_id": "A-500", "utilisation_pct": 250})
    assert bad.status_code == 422  # out-of-range quarantined


def test_predict_needs_telemetry():
    client.post("/assets", json={
        "asset_id": "A-600", "name": "NoData", "category": "Computing Hardware",
        "purchase_date": "2023-01-01", "purchase_price": 50000, "is_iot_enabled": True,
    })
    r = client.post("/maintenance/A-600/predict")
    assert r.status_code == 400  # no telemetry yet


def test_full_predict_flow():
    client.post("/assets", json={
        "asset_id": "A-700", "name": "Predictable", "category": "Computing Hardware",
        "purchase_date": "2023-01-01", "purchase_price": 50000, "is_iot_enabled": True,
    })
    client.post("/telemetry", json={
        "asset_id": "A-700", "temperature_c": 100, "utilisation_pct": 95,
        "fault_code": 3, "battery_pct": 15, "uptime_hours": 8000,
    })
    r = client.post("/maintenance/A-700/predict")
    assert r.status_code == 200
    assert r.json()["urgency"] in ("Low", "Medium", "High")


def test_depreciation_compute():
    client.post("/assets", json={
        "asset_id": "A-800", "name": "DepAsset", "category": "Office Equipment",
        "purchase_date": "2022-01-01", "purchase_price": 40000,
        "useful_life_yrs": 4, "depr_method": "straight_line",
    })
    r = client.post("/depreciation/A-800/compute")
    assert r.status_code == 200
    body = r.json()
    assert round(body["accumulated_depr"] + body["net_book_value"], 2) == 40000


def test_powerbi_feeds():
    assert client.get("/feeds/asset-health").status_code == 200
    assert client.get("/feeds/maintenance-schedule").status_code == 200
    assert client.get("/feeds/depreciation").status_code == 200
