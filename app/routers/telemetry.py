from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import orm, schemas

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

# Guardrail ranges (proposal 5.4: out-of-range values quarantined, not written)
RANGES = {
    "temperature_c": (-20, 120),
    "utilisation_pct": (0, 100),
    "battery_pct": (0, 100),
}


def validate_payload(t: schemas.TelemetryIn):
    for field, (lo, hi) in RANGES.items():
        val = getattr(t, field)
        if val is not None and not (lo <= val <= hi):
            raise HTTPException(422, f"{field}={val} out of range [{lo},{hi}] - quarantined")


@router.post("", response_model=schemas.TelemetryOut)
def ingest(t: schemas.TelemetryIn, db: Session = Depends(get_db)):
    if not db.get(orm.Asset, t.asset_id):
        raise HTTPException(404, f"Unknown asset {t.asset_id}")
    validate_payload(t)
    obj = orm.Telemetry(**t.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{asset_id}", response_model=List[schemas.TelemetryOut])
def get_telemetry(asset_id: str, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(orm.Telemetry)
        .filter(orm.Telemetry.asset_id == asset_id)
        .order_by(orm.Telemetry.ts.desc())
        .limit(limit)
        .all()
    )
