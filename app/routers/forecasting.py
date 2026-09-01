from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import pandas as pd

from app.database import get_db
from app.models import orm
from app.services import forecasting as fc_service

router = APIRouter(prefix="/forecast", tags=["forecast"])


def _risk_history_df(db: Session, asset_id: str) -> pd.DataFrame:
    """Build a (ds, y) risk-over-time frame from an asset's telemetry, using
    the same risk ingredients the ML model reasons about (temperature,
    utilisation, faults, battery), so the forecast is consistent with why
    the maintenance model flags an asset.
    """
    rows = (
        db.query(orm.Telemetry)
        .filter(orm.Telemetry.asset_id == asset_id)
        .order_by(orm.Telemetry.ts.asc())
        .all()
    )
    data = []
    for t in rows:
        temp = float(t.temperature_c) if t.temperature_c is not None else 50.0
        util = float(t.utilisation_pct) if t.utilisation_pct is not None else 50.0
        batt = float(t.battery_pct) if t.battery_pct is not None else 80.0
        fault = 1.0 if (t.fault_code or 0) > 0 else 0.0
        risk = (
            0.4 * min(max(temp - 40, 0) / 60, 1)
            + 0.3 * min(util / 100, 1)
            + 0.2 * fault
            + 0.1 * min(max(80 - batt, 0) / 80, 1)
        )
        data.append({"ds": t.ts.date() if hasattr(t.ts, "date") else t.ts, "y": min(risk, 1.0)})
    return pd.DataFrame(data)


@router.post("/{asset_id}/depreciation")
def forecast_depreciation(asset_id: str, horizon_months: int = 12, db: Session = Depends(get_db)):
    """Prophet forecast of net book value for the next `horizon_months`.
    Stored as forecast_type='depreciation' rows in the forecasts table.
    """
    asset = db.get(orm.Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")

    history = db.query(orm.Depreciation).filter(orm.Depreciation.asset_id == asset_id).all()
    history_df = None
    if len(history) >= 3:
        history_df = pd.DataFrame(
            [{"ds": h.as_of_date, "y": float(h.net_book_value)} for h in history]
        )

    points = fc_service.forecast_depreciation(asset, history_df, horizon_months)
    if not points:
        raise HTTPException(400, "Not enough data to forecast yet")

    db.query(orm.Forecast).filter(
        orm.Forecast.asset_id == asset_id, orm.Forecast.forecast_type == "depreciation"
    ).delete()
    for p in points:
        db.add(orm.Forecast(asset_id=asset_id, forecast_type="depreciation", **p))
    db.commit()
    return {"asset_id": asset_id, "forecast_type": "depreciation", "points": points}


@router.post("/{asset_id}/maintenance-windows")
def forecast_maintenance_windows(asset_id: str, horizon_days: int = 30, db: Session = Depends(get_db)):
    """Prophet forecast of the risk trend for the next `horizon_days`, so
    upcoming maintenance windows can be seen clustering over time instead
    of relying on a single latest-reading prediction (that's what the
    scikit-learn model in app/ml already does). Stored as
    forecast_type='maintenance_window' rows in the forecasts table.
    """
    asset = db.get(orm.Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")

    telemetry_df = _risk_history_df(db, asset_id)
    points = fc_service.forecast_maintenance_window(telemetry_df, horizon_days)
    if not points:
        raise HTTPException(400, "Not enough telemetry history to forecast yet (need 5+ readings)")

    db.query(orm.Forecast).filter(
        orm.Forecast.asset_id == asset_id, orm.Forecast.forecast_type == "maintenance_window"
    ).delete()
    for p in points:
        db.add(orm.Forecast(asset_id=asset_id, forecast_type="maintenance_window", **p))
    db.commit()
    return {"asset_id": asset_id, "forecast_type": "maintenance_window", "points": points}


@router.get("/{asset_id}")
def get_forecasts(asset_id: str, forecast_type: str | None = None, db: Session = Depends(get_db)):
    q = db.query(orm.Forecast).filter(orm.Forecast.asset_id == asset_id)
    if forecast_type:
        q = q.filter(orm.Forecast.forecast_type == forecast_type)
    rows = q.order_by(orm.Forecast.ds.asc()).all()
    return [
        {"asset_id": r.asset_id, "forecast_type": r.forecast_type, "ds": r.ds,
         "yhat": float(r.yhat), "yhat_lower": float(r.yhat_lower), "yhat_upper": float(r.yhat_upper)}
        for r in rows
    ]
