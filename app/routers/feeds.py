"""Flat, dashboard-friendly endpoints Power BI connects to via Web connector."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import orm

router = APIRouter(prefix="/feeds", tags=["powerbi"])


@router.get("/asset-health")
def asset_health(db: Session = Depends(get_db)):
    """One row per asset with its latest telemetry + latest alert urgency."""
    out = []
    for a in db.query(orm.Asset).all():
        t = (db.query(orm.Telemetry).filter(orm.Telemetry.asset_id == a.asset_id)
             .order_by(orm.Telemetry.ts.desc()).first())
        al = (db.query(orm.MaintenanceAlert).filter(orm.MaintenanceAlert.asset_id == a.asset_id)
              .order_by(orm.MaintenanceAlert.created_at.desc()).first())
        out.append({
            "asset_id": a.asset_id, "name": a.name, "category": a.category,
            "location": a.location,
            "temperature_c": float(t.temperature_c) if t and t.temperature_c else None,
            "utilisation_pct": float(t.utilisation_pct) if t and t.utilisation_pct else None,
            "fault_code": int(t.fault_code) if t else None,
            "urgency": al.urgency if al else "None",
            "predicted_days": al.predicted_days if al else None,
        })
    return out


@router.get("/maintenance-schedule")
def maintenance_schedule(db: Session = Depends(get_db)):
    rows = db.query(orm.MaintenanceAlert).order_by(orm.MaintenanceAlert.created_at.desc()).all()
    return [{
        "asset_id": r.asset_id, "created_at": r.created_at,
        "urgency": r.urgency, "predicted_days": r.predicted_days,
        "confidence": float(r.confidence) if r.confidence else None,
        "explanation": r.gemini_explanation,
    } for r in rows]


@router.get("/depreciation")
def depreciation_feed(db: Session = Depends(get_db)):
    rows = db.query(orm.Depreciation).all()
    return [{
        "asset_id": r.asset_id, "as_of_date": r.as_of_date, "method": r.method,
        "accumulated_depr": float(r.accumulated_depr),
        "net_book_value": float(r.net_book_value),
    } for r in rows]


@router.get("/forecasts")
def forecasts_feed(forecast_type: str | None = None, db: Session = Depends(get_db)):
    """Flat feed of Prophet forecast points, for the replacement-forecast /
    depreciation-trend Power BI views."""
    q = db.query(orm.Forecast)
    if forecast_type:
        q = q.filter(orm.Forecast.forecast_type == forecast_type)
    rows = q.order_by(orm.Forecast.asset_id, orm.Forecast.ds).all()
    return [{
        "asset_id": r.asset_id, "forecast_type": r.forecast_type, "ds": r.ds,
        "yhat": float(r.yhat), "yhat_lower": float(r.yhat_lower), "yhat_upper": float(r.yhat_upper),
    } for r in rows]
