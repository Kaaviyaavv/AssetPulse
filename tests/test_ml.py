"""scikit-learn model tests with synthetic fixtures (proposal 5.2)."""
from app.ml.maintenance import MaintenanceModel, get_model


def test_model_trains():
    m = MaintenanceModel().train()
    assert m.trained


def test_healthy_asset_low_urgency():
    m = get_model()
    pred = m.predict({
        "temperature_c": 45, "utilisation_pct": 30, "fault_code": 0,
        "battery_pct": 90, "uptime_hours": 500,
    })
    assert pred["urgency"] in ("Low", "Medium")
    assert pred["predicted_days"] > 0


def test_stressed_asset_high_urgency():
    m = get_model()
    pred = m.predict({
        "temperature_c": 105, "utilisation_pct": 98, "fault_code": 4,
        "battery_pct": 10, "uptime_hours": 8500,
    })
    assert pred["urgency"] in ("Medium", "High")


def test_prediction_shape():
    pred = get_model().predict({"temperature_c": 60})
    assert set(pred) == {"urgency", "predicted_days", "confidence", "key_features"}
    assert 0 <= pred["confidence"] <= 1
