from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app.models import orm, schemas
from app.services import depreciation as depr

router = APIRouter(prefix="/depreciation", tags=["depreciation"])


@router.post("/{asset_id}/compute", response_model=schemas.DepreciationOut)
def compute_depreciation(asset_id: str, db: Session = Depends(get_db)):
    a = db.get(orm.Asset, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    as_of = date.today()
    acc, nbv = depr.compute(
        float(a.purchase_price), a.useful_life_yrs, a.depr_method,
        a.purchase_date, as_of
    )
    # upsert: delete any existing snapshot for same asset/date/method, then insert
    db.query(orm.Depreciation).filter(
        orm.Depreciation.asset_id == asset_id,
        orm.Depreciation.as_of_date == as_of,
        orm.Depreciation.method == a.depr_method,
    ).delete()
    row = orm.Depreciation(
        asset_id=asset_id, as_of_date=as_of, method=a.depr_method,
        accumulated_depr=acc, net_book_value=nbv,
    )
    db.add(row)
    db.commit()
    return schemas.DepreciationOut(
        asset_id=asset_id, as_of_date=as_of, method=a.depr_method,
        accumulated_depr=acc, net_book_value=nbv,
    )
