"""Tests for Prophet-based forecasting (app/services/forecasting.py,
app/routers/forecasting.py). Covers the UC-05 midterm-feedback gap.

Uses its own in-memory SQLite DB, same pattern as test_api.py, so this
file can run standalone.
"""
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

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


def _make_asset(asset_id="F-001", days_old=800):
    client.post("/assets", json={
        "asset_id": asset_id, "name": "Forecast Test Server",
        "category": "Server & Networking",
        "purchase_date": str(date.today() - timedelta(days=days_old)),
        "purchase_price": 200000, "useful_life_yrs": 5,
        "depr_method": "diminishing_balance", "is_iot_enabled": True,
    })
    return asset_id


def test_depreciation_forecast_returns_points_and_persists():
    aid = _make_asset("F-001")
    r = client.post(f"/forecast/{aid}/depreciation?horizon_months=6")
    assert r.status_code == 200
    body = r.json()
    assert body["forecast_type"] == "depreciation"
    assert len(body["points"]) == 6
    for p in body["points"]:
        assert p["yhat"] >= 0
        # net book value can never exceed purchase price
        assert p["yhat"] <= 200000

    # persisted -> retrievable via GET
    got = client.get(f"/forecast/{aid}?forecast_type=depreciation")
    assert got.status_code == 200
    assert len(got.json()) == 6


def test_depreciation_forecast_unknown_asset_404():
    r = client.post("/forecast/DOES-NOT-EXIST/depreciation")
    assert r.status_code == 404


def test_maintenance_window_forecast_needs_telemetry():
    aid = _make_asset("F-002")
    # no telemetry sent yet -> not enough history
    r = client.post(f"/forecast/{aid}/maintenance-windows")
    assert r.status_code == 400


def test_maintenance_window_forecast_with_telemetry():
    aid = _make_asset("F-003")
    # feed in a rising-risk trend so Prophet has a real signal to fit
    for i in range(10):
        client.post("/telemetry", json={
            "asset_id": aid,
            "temperature_c": 45 + i * 3,
            "utilisation_pct": 40 + i * 4,
            "fault_code": 1 if i > 7 else 0,
            "battery_pct": 90 - i * 5,
            "uptime_hours": 5000,
        })
    r = client.post(f"/forecast/{aid}/maintenance-windows?horizon_days=14")
    assert r.status_code == 200
    body = r.json()
    assert body["forecast_type"] == "maintenance_window"
    assert len(body["points"]) == 14
    for p in body["points"]:
        assert 0 <= p["yhat"] <= 1

    got = client.get(f"/forecast/{aid}?forecast_type=maintenance_window")
    assert len(got.json()) == 14


def test_forecasts_feed_for_powerbi():
    aid = _make_asset("F-004")
    client.post(f"/forecast/{aid}/depreciation?horizon_months=3")
    r = client.get("/feeds/forecasts?forecast_type=depreciation")
    assert r.status_code == 200
    rows = [row for row in r.json() if row["asset_id"] == aid]
    assert len(rows) == 3

