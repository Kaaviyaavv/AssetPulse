"""Seed 25+ assets across 4 categories via the running API.
Run:  python simulator/seed_assets.py
"""
import requests
from datetime import date, timedelta
import random

API = "http://localhost:8000"

CATEGORIES = {
    "Computing Hardware": ("Dell Latitude", "laptop", True, 65000, "straight_line"),
    "Server & Networking": ("HP ProLiant", "server", True, 250000, "diminishing_balance"),
    "AV & Presentation": ("Epson Projector", "projector", False, 45000, "straight_line"),
    "Office Equipment": ("APC UPS", "ups", True, 30000, "straight_line"),
}
COUNTS = {"Computing Hardware": 10, "Server & Networking": 7,
          "AV & Presentation": 4, "Office Equipment": 4}

LOCATIONS = ["Chennai HQ", "Pune Office", "Server Room A", "Floor 2", "Floor 3"]


def main():
    idx = 1
    created = 0
    for cat, count in COUNTS.items():
        base_name, kind, iot, price, method = CATEGORIES[cat]
        for _ in range(count):
            aid = f"A-{idx:03d}"
            payload = {
                "asset_id": aid,
                "name": f"{base_name} {idx}",
                "category": cat,
                "manufacturer": base_name.split()[0],
                "model": kind,
                "purchase_date": str(date.today() - timedelta(days=random.randint(120, 1200))),
                "purchase_price": price + random.randint(-5000, 5000),
                "useful_life_yrs": random.choice([3, 4, 5]),
                "depr_method": method,
                "is_iot_enabled": iot,
                "location": random.choice(LOCATIONS),
                "assigned_to": random.choice(["IT Ops", "Finance", "Facilities"]),
            }
            r = requests.post(f"{API}/assets", json=payload)
            if r.status_code == 200:
                created += 1
            else:
                print(f"  {aid}: {r.status_code} {r.text[:80]}")
            idx += 1
    print(f"Created {created} assets.")


if __name__ == "__main__":
    main()
