"""Predictive maintenance models.

Random Forest  -> classifies urgency (Low / Medium / High)
Gradient Boost -> predicts remaining useful life in days
Ensemble       -> combines both into a final maintenance-window prediction

Trained on telemetry features. For the demo we train on synthetic data
generated from asset telemetry history (proposal 3.5).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor

FEATURES = ["temperature_c", "utilisation_pct", "fault_code", "battery_pct", "uptime_hours"]


def _synthesise_training_data(n=2000, seed=42):
    """Create labelled synthetic telemetry so the models have something to learn.
    Higher temp + utilisation + faults => higher urgency, fewer days left."""
    rng = np.random.default_rng(seed)
    temp = rng.normal(55, 15, n).clip(20, 110)
    util = rng.normal(60, 20, n).clip(0, 100)
    fault = rng.binomial(1, 0.1, n) * rng.integers(1, 5, n)
    batt = rng.normal(70, 20, n).clip(0, 100)
    uptime = rng.normal(4000, 1500, n).clip(0, 9000)

    # risk score drives both labels
    risk = (temp - 40) / 70 + util / 100 + fault / 4 + uptime / 9000 - batt / 200
    risk = (risk - risk.min()) / (risk.max() - risk.min())

    urgency = np.where(risk > 0.66, "High", np.where(risk > 0.4, "Medium", "Low"))
    days_left = ((1 - risk) * 120 + rng.normal(0, 5, n)).clip(1, 180).astype(int)

    df = pd.DataFrame({
        "temperature_c": temp, "utilisation_pct": util, "fault_code": fault,
        "battery_pct": batt, "uptime_hours": uptime,
        "urgency": urgency, "days_left": days_left,
    })
    return df


class MaintenanceModel:
    def __init__(self):
        self.clf = RandomForestClassifier(n_estimators=120, random_state=42)
        self.reg = GradientBoostingRegressor(random_state=42)
        self.trained = False

    def train(self, df: pd.DataFrame = None):
        if df is None:
            df = _synthesise_training_data()
        X = df[FEATURES].fillna(0)
        self.clf.fit(X, df["urgency"])
        self.reg.fit(X, df["days_left"])
        self.trained = True
        return self

    def predict(self, features: dict):
        """features: dict with the 5 telemetry keys. Returns ensemble result."""
        X = pd.DataFrame([{f: features.get(f, 0) or 0 for f in FEATURES}])
        urgency = self.clf.predict(X)[0]
        proba = float(self.clf.predict_proba(X).max())
        days = int(round(self.reg.predict(X)[0]))
        # ensemble rule: if regressor says <14 days, force at least Medium
        if days < 14 and urgency == "Low":
            urgency = "Medium"
        return {
            "urgency": urgency,
            "predicted_days": days,
            "confidence": round(proba, 4),
            "key_features": {f: features.get(f) for f in FEATURES},
        }


# module-level singleton, trained lazily on first use
_model = None


def get_model() -> MaintenanceModel:
    global _model
    if _model is None:
        _model = MaintenanceModel().train()
    return _model
