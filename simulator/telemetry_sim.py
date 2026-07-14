"""IoT telemetry simulator - stands in for Azure IoT Hub for the demo.

Sends telemetry payloads to the FastAPI ingestion endpoint, just like a
real device would. Proposal Risk #1 fallback: "use pre-built dataset /
simulator instead of live Azure".

Modes:
  python simulator/telemetry_sim.py --history   # backfill 40 points/asset (for ML training)
  python simulator/telemetry_sim.py --live       # stream every few seconds (for demo)
"""
import requests
import random
import time
import argparse
from datetime import datetime, timedelta

API = "http://localhost:8000"


def iot_assets():
    assets = requests.get(f"{API}/assets").json()
    return [a for a in assets if a["is_iot_enabled"]]


def make_payload(asset_id, degrade=0.0):
    """degrade 0..1 nudges an asset toward failure-looking telemetry."""
    return {
        "asset_id": asset_id,
        "temperature_c": round(random.uniform(40, 60) + degrade * 40, 1),
        "utilisation_pct": round(random.uniform(30, 70) + degrade * 25, 1),
        "fault_code": 1 if random.random() < 0.05 + degrade * 0.3 else 0,
        "battery_pct": round(random.uniform(40, 100) - degrade * 30, 1),
        "uptime_hours": round(random.uniform(1000, 6000), 1),
    }


def backfill(points=40):
    assets = iot_assets()
    print(f"Backfilling {points} points for {len(assets)} IoT assets...")
    total = 0
    for i, a in enumerate(assets):
        # make a couple of assets trend toward failure so alerts fire
        trend = 0.02 if i < 2 else 0.0
        for p in range(points):
            degrade = min(trend * p, 0.9)
            payload = make_payload(a["asset_id"], degrade)
            payload["utilisation_pct"] = min(payload["utilisation_pct"], 100)
            payload["battery_pct"] = max(payload["battery_pct"], 0)
            r = requests.post(f"{API}/telemetry", json=payload)
            if r.status_code == 200:
                total += 1
    print(f"Inserted {total} telemetry rows.")


def live(interval=5):
    assets = iot_assets()
    print(f"Live streaming for {len(assets)} assets every {interval}s. Ctrl-C to stop.")
    try:
        while True:
            for a in assets:
                requests.post(f"{API}/telemetry", json=make_payload(a["asset_id"]))
            print(f"{datetime.now():%H:%M:%S} sent {len(assets)} payloads")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("stopped.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", action="store_true", help="backfill history for ML")
    ap.add_argument("--live", action="store_true", help="stream continuously")
    ap.add_argument("--points", type=int, default=40)
    args = ap.parse_args()
    if args.history:
        backfill(args.points)
    elif args.live:
        live()
    else:
        print("pass --history or --live")
