"""Prophet-based time-series forecasting.

Two forecast types, both written to the `forecasts` table (forecast_type
distinguishes them):

  - "depreciation": projects net book value forward using Prophet, fit on
    the asset's own historical depreciation snapshots (or, if there aren't
    enough snapshots yet, on a synthetic history derived from the
    depreciation formula in services/depreciation.py). This is the
    "depreciation curve forecast" named in the proposal.

  - "maintenance_window": projects the next likely maintenance-need windows
    from the asset's telemetry-driven risk trend over time, so operations
    can see clustering of upcoming maintenance rather than a single
    snapshot prediction.

Kept deliberately simple (Prophet's defaults) since the point for this
project is a working, explainable forecast pipeline, not a tuned model.
"""
from datetime import date, timedelta
import pandas as pd
from prophet import Prophet

from app.services import depreciation as depr


def _quiet_prophet():
    """Prophet/cmdstanpy are chatty by default; keep logs out of API responses."""
    import logging
    for name in ("prophet", "cmdstanpy"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _synthetic_depreciation_history(asset, as_of: date, points: int = 12):
    """Build a monthly net-book-value history for an asset up to today.

    Used when we don't yet have enough real Depreciation snapshots stored
    to fit Prophet on. Reuses the exact same depreciation math as the rest
    of the app (services/depreciation.py), so the "forecast" starts from
    numbers consistent with the compute endpoint - it's just projecting the
    same curve forward with Prophet instead of a hand-written extrapolation.
    """
    rows = []
    for i in range(points, -1, -1):
        d = as_of - timedelta(days=30 * i)
        if d < asset.purchase_date:
            continue
        _, nbv = depr.compute(
            float(asset.purchase_price), asset.useful_life_yrs,
            asset.depr_method, asset.purchase_date, d,
        )
        rows.append({"ds": d, "y": nbv})
    return pd.DataFrame(rows)


def _linear_fallback(df: pd.DataFrame, periods: int, freq: str, lo_hi: tuple[float, float]):
    """Simple linear-trend projection, used only if Prophet's optimizer
    fails to converge (rare, data-dependent). Keeps the endpoint reliable
    even when Prophet itself has trouble - the same "never crash, degrade
    gracefully" approach used for the Gemini/Groq calls in services/ai.py.
    """
    df = df.sort_values("ds").reset_index(drop=True)
    n = len(df)
    x = list(range(n))
    y = df["y"].tolist()
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    denom = sum((xi - x_mean) ** 2 for xi in x) or 1.0
    slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y)) / denom
    intercept = y_mean - slope * x_mean
    spread = (max(y) - min(y)) * 0.1 or 1.0

    last_ds = df["ds"].iloc[-1]
    lo, hi = lo_hi
    points = []
    for i in range(1, periods + 1):
        ds = last_ds + (timedelta(days=30 * i) if freq == "MS" else timedelta(days=i))
        yhat = min(max(intercept + slope * (n - 1 + i), lo), hi)
        points.append({
            "ds": ds, "yhat": round(yhat, 4),
            "yhat_lower": round(max(yhat - spread, lo), 4),
            "yhat_upper": round(min(yhat + spread, hi), 4),
        })
    return points


def _fit_and_predict(df: pd.DataFrame, periods: int, freq: str, lo_hi: tuple[float, float]):
    """Fit Prophet and predict; fall back to a linear trend if Stan fails."""
    try:
        m = Prophet(yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False)
        m.fit(df)
        future = m.make_future_dataframe(periods=periods, freq=freq, include_history=False)
        fc = m.predict(future)
        lo, hi = lo_hi
        fc["yhat"] = fc["yhat"].clip(lower=lo, upper=hi)
        fc["yhat_lower"] = fc["yhat_lower"].clip(lower=lo, upper=hi)
        fc["yhat_upper"] = fc["yhat_upper"].clip(lower=lo, upper=hi)
        return [
            {"ds": row.ds.date(), "yhat": round(row.yhat, 4),
             "yhat_lower": round(row.yhat_lower, 4), "yhat_upper": round(row.yhat_upper, 4)}
            for row in fc.itertuples()
        ]
    except Exception:
        return _linear_fallback(df, periods, freq, lo_hi)


def forecast_depreciation(asset, history_df: pd.DataFrame | None, horizon_months: int = 12):
    """Return a list of {ds, yhat, yhat_lower, yhat_upper} dicts, one per
    future month, projecting net book value forward `horizon_months`.
    """
    _quiet_prophet()
    as_of = date.today()
    df = history_df if history_df is not None and len(history_df) >= 3 else None
    if df is None:
        df = _synthetic_depreciation_history(asset, as_of)
    if len(df) < 2:
        return []

    price = float(asset.purchase_price)
    return _fit_and_predict(df, horizon_months, "MS", (0, price))


def forecast_maintenance_window(telemetry_df: pd.DataFrame, horizon_days: int = 30):
    """Given a per-reading risk score over time (ds, y=risk 0..1), forecast
    the risk trend `horizon_days` ahead so upcoming maintenance windows can
    be seen clustering, rather than relying on a single latest-reading
    prediction. Returns a list of {ds, yhat, yhat_lower, yhat_upper}.
    """
    _quiet_prophet()
    if telemetry_df is None or len(telemetry_df) < 5:
        return []

    return _fit_and_predict(telemetry_df, horizon_days, "D", (0, 1))
