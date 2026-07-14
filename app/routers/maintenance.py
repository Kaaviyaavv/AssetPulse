from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import orm, schemas
from app.ml.maintenance import get_model
from app.services.ai import gemini_explain, groq_health_query

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

ALERT_THRESHOLD_DAYS = 21  # fire an alert if predicted maintenance is within this window


def _latest_features(db: Session, asset_id: str) -> dict:
    t = (db.query(orm.Telemetry)
         .filter(orm.Telemetry.asset_id == asset_id)
         .order_by(orm.Telemetry.ts.desc()).first())
    if not t:
        return None
    return {
        "temperature_c": float(t.temperature_c or 0),
        "utilisation_pct": float(t.utilisation_pct or 0),
        "fault_code": int(t.fault_code or 0),
        "battery_pct": float(t.battery_pct or 0),
        "uptime_hours": float(t.uptime_hours or 0),
    }


@router.post("/{asset_id}/predict", response_model=schemas.AlertOut)
def predict_and_alert(asset_id: str, db: Session = Depends(get_db)):
    asset = db.get(orm.Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    feats = _latest_features(db, asset_id)
    if feats is None:
        raise HTTPException(400, "No telemetry for this asset yet")

    pred = get_model().predict(feats)

    explanation = None
    if pred["predicted_days"] <= ALERT_THRESHOLD_DAYS or pred["urgency"] == "High":
        explanation = gemini_explain(asset_id, asset.name, pred)

    alert = orm.MaintenanceAlert(
        asset_id=asset_id,
        urgency=pred["urgency"],
        predicted_days=pred["predicted_days"],
        confidence=pred["confidence"],
        key_features=pred["key_features"],
        gemini_explanation=explanation,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/alerts", response_model=list[schemas.AlertOut])
def list_alerts(db: Session = Depends(get_db)):
    return db.query(orm.MaintenanceAlert).order_by(orm.MaintenanceAlert.created_at.desc()).all()


class HealthQuery(BaseModel):
    question: str
    category: str | None = None


@router.post("/health-query")
def health_query(q: HealthQuery, db: Session = Depends(get_db)):
    """Groq real-time health query over current telemetry."""
    query = db.query(orm.Asset)
    if q.category:
        query = query.filter(orm.Asset.category == q.category)
    assets = query.all()
    lines = []
    for a in assets:
        f = _latest_features(db, a.asset_id)
        if f:
            lines.append(f"{a.asset_id} ({a.name}): temp={f['temperature_c']}C "
                         f"util={f['utilisation_pct']}% fault={f['fault_code']} "
                         f"battery={f['battery_pct']}%")
    context = "\n".join(lines) if lines else "No telemetry available."
    answer = groq_health_query(q.question, context)
    return {"question": q.question, "answer": answer, "assets_considered": len(lines)}
