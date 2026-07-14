from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, DateTime, Date, BigInteger,
    ForeignKey, JSON, Text
)
from sqlalchemy.sql import func
from app.database import Base

# BigInteger autoincrements on Postgres but NOT on SQLite (used in tests).
# This variant maps to plain INTEGER on SQLite so autoincrement works everywhere.
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class Asset(Base):
    __tablename__ = "assets"
    asset_id = Column(String(20), primary_key=True)
    name = Column(String(120), nullable=False)
    category = Column(String(60), nullable=False)
    manufacturer = Column(String(80))
    model = Column(String(80))
    purchase_date = Column(Date, nullable=False)
    purchase_price = Column(Numeric(12, 2), nullable=False)
    useful_life_yrs = Column(Integer, nullable=False, default=5)
    depr_method = Column(String(30), nullable=False, default="straight_line")
    is_iot_enabled = Column(Boolean, nullable=False, default=False)
    location = Column(String(120))
    assigned_to = Column(String(120))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Telemetry(Base):
    __tablename__ = "telemetry"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    asset_id = Column(String(20), ForeignKey("assets.asset_id"), nullable=False)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    temperature_c = Column(Numeric(6, 2))
    utilisation_pct = Column(Numeric(6, 2))
    fault_code = Column(Integer, default=0)
    battery_pct = Column(Numeric(6, 2))
    uptime_hours = Column(Numeric(10, 2))


class MaintenanceAlert(Base):
    __tablename__ = "maintenance_alerts"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    asset_id = Column(String(20), ForeignKey("assets.asset_id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    urgency = Column(String(10), nullable=False)
    predicted_days = Column(Integer)
    confidence = Column(Numeric(5, 4))
    key_features = Column(JSON)
    gemini_explanation = Column(Text)


class Depreciation(Base):
    __tablename__ = "depreciation"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    asset_id = Column(String(20), ForeignKey("assets.asset_id"), nullable=False)
    as_of_date = Column(Date, nullable=False)
    method = Column(String(30), nullable=False)
    accumulated_depr = Column(Numeric(12, 2), nullable=False)
    net_book_value = Column(Numeric(12, 2), nullable=False)


class Forecast(Base):
    __tablename__ = "forecasts"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    asset_id = Column(String(20), ForeignKey("assets.asset_id"), nullable=False)
    forecast_type = Column(String(30), nullable=False)
    ds = Column(Date, nullable=False)
    yhat = Column(Numeric(14, 4))
    yhat_lower = Column(Numeric(14, 4))
    yhat_upper = Column(Numeric(14, 4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
