from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import orm, schemas

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=schemas.AssetOut)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    if db.get(orm.Asset, asset.asset_id):
        raise HTTPException(400, f"Asset {asset.asset_id} already exists")
    obj = orm.Asset(**asset.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("", response_model=List[schemas.AssetOut])
def list_assets(db: Session = Depends(get_db)):
    return db.query(orm.Asset).all()


@router.get("/{asset_id}", response_model=schemas.AssetOut)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    obj = db.get(orm.Asset, asset_id)
    if not obj:
        raise HTTPException(404, "Asset not found")
    return obj


@router.put("/{asset_id}", response_model=schemas.AssetOut)
def update_asset(asset_id: str, asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    obj = db.get(orm.Asset, asset_id)
    if not obj:
        raise HTTPException(404, "Asset not found")
    for k, v in asset.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{asset_id}")
def delete_asset(asset_id: str, db: Session = Depends(get_db)):
    obj = db.get(orm.Asset, asset_id)
    if not obj:
        raise HTTPException(404, "Asset not found")
    db.delete(obj)
    db.commit()
    return {"deleted": asset_id}
