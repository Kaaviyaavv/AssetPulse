from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


# ---------- Assets ----------
class AssetCreate(BaseModel):
    asset_id: str = Field(..., examples=["A-001"])
    name: str
    category: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    purchase_date: date
    purchase_price: float
    useful_life_yrs: int = 5
    depr_method: str = "straight_line"          # or "diminishing_balance"
    is_iot_enabled: bool = False
    location: Optional[str] = None
    assigned_to: Optional[str] = None


class AssetOut(AssetCreate):
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Telemetry ----------
class TelemetryIn(BaseModel):
    asset_id: str
    temperature_c: Optional[float] = None
    utilisation_pct: Optional[float] = None
    fault_code: int = 0
    battery_pct: Optional[float] = None
    uptime_hours: Optional[float] = None


class TelemetryOut(TelemetryIn):
    id: int
    ts: datetime

    class Config:
        from_attributes = True


# ---------- Alerts ----------
class AlertOut(BaseModel):
    id: int
    asset_id: str
    created_at: datetime
    urgency: str
    predicted_days: Optional[int]
    confidence: Optional[float]
    gemini_explanation: Optional[str]

    class Config:
        from_attributes = True


# ---------- Depreciation ----------
class DepreciationOut(BaseModel):
    asset_id: str
    as_of_date: date
    method: str
    accumulated_depr: float
    net_book_value: float

    class Config:
        from_attributes = True
