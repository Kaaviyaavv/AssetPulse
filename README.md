# AssetPulse — Local Setup & Midterm Build Guide

Asset Tracking & Management System · IMPACT pSiddhi 3.0 · Topic S2-C-10

This project runs **entirely on your local machine** — no Azure needed for the
midterm. A Python simulator stands in for Azure IoT Hub (your proposal's own
Risk #1 fallback). You add real Azure IoT Hub later for the final if you want.

Everything below is already built and tested (18 tests passing, 86% coverage).

---

## What you need installed

- **Python 3.11+** (you have VS Code — good)
- **Docker Desktop** (for PostgreSQL) — OR skip Docker and use SQLite (see note)
- **pgAdmin 4** (you have it — to inspect the database)
- **Power BI Desktop** (you have it — for dashboards)

---

## STEP 1 — Get the code into VS Code

1. Unzip the folder and open it in VS Code (`File > Open Folder`).
2. Open a terminal in VS Code (`Ctrl+\``).

## STEP 2 — Create a Python virtual environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

> `prophet`, `google-generativeai`, and `groq` are in requirements.txt but are
> only needed for Phase 2 (weeks 11+). If any fail to install now, comment them
> out — the midterm core works without them.

## STEP 3 — Start PostgreSQL

**Option A — Docker (matches your proposal):**
```bash
docker compose up -d
```
This starts Postgres on `localhost:5432` and auto-creates all tables from
`sql/init.sql`. Verify in pgAdmin 4: connect to `localhost:5432`, user
`assetpulse`, password `assetpulse_pw`, database `assetpulse`.

**Option B — No Docker (fastest):** skip Docker entirely and use SQLite. In
your `.env` set:
```
DATABASE_URL=sqlite:///./assetpulse.db
```
The app creates the tables automatically. (Use Docker/Postgres for the real
submission though — it's what the proposal commits to.)

## STEP 4 — Configure environment

```bash
cp .env.example .env      # Windows: copy .env.example .env
```
For now you can leave the API keys blank — the AI layer has offline fallbacks
so everything runs. Add real keys when you're ready (Step 8).

## STEP 5 — Run the API

```bash
uvicorn app.main:app --reload --port 8000
```
Open **http://localhost:8000/docs** — interactive Swagger UI for every endpoint.
Take screenshots here for your midterm evidence.

## STEP 6 — Seed data and simulate telemetry

In a **second terminal** (keep the server running):
```bash
python simulator/seed_assets.py            # creates 25 assets, 4 categories
python simulator/telemetry_sim.py --history --points 40   # ~840 telemetry rows
```

For a live demo, stream telemetry continuously:
```bash
python simulator/telemetry_sim.py --live
```

## STEP 7 — Generate predictions, alerts, depreciation

```bash
# Predict + alert for assets (do 5+ for midterm)
curl -X POST http://localhost:8000/maintenance/A-001/predict
# Compute depreciation for assets (do 15+ for midterm)
curl -X POST http://localhost:8000/depreciation/A-001/compute
```
Or just click **Execute** on these endpoints in `/docs`.

Real-time health query (Groq):
```bash
curl -X POST http://localhost:8000/maintenance/health-query \
  -H "Content-Type: application/json" \
  -d '{"question":"Which assets look unhealthy?","category":"Server & Networking"}'
```

## STEP 8 — Add AI keys (when ready)

- **Gemini** (free): https://aistudio.google.com/apikey → paste into `.env` as `GEMINI_API_KEY`
- **Groq** (free): https://console.groq.com/keys → paste into `.env` as `GROQ_API_KEY`

Restart the server. Now maintenance alerts get real plain-English Gemini
explanations, and health queries get real Groq answers.

## STEP 9 — Run tests (midterm deliverable)

```bash
pytest --cov=app --cov-report=term-missing
```
18 tests, ~86% coverage. Screenshot this for your evidence.

## STEP 10 — Connect Power BI

1. Open Power BI Desktop → **Get Data > Web**.
2. Enter each feed URL:
   - `http://localhost:8000/feeds/asset-health`
   - `http://localhost:8000/feeds/maintenance-schedule`
   - `http://localhost:8000/feeds/depreciation`
3. Power BI parses the JSON into tables. Build 2 views for midterm:
   - **Asset Health** — cards/table of urgency by asset, colour-coded
   - **Maintenance Schedule** — alerts list with predicted_days
4. Keep the API server running while Power BI refreshes.

---

## Midterm (Week 10) checklist — how each item is covered

| Requirement | Where it lives |
|---|---|
| Telemetry ingestion, 3+ assets, 2+ signals | `simulator/telemetry_sim.py` + `POST /telemetry` |
| FastAPI CRUD + telemetry + maintenance + depreciation | `app/routers/` |
| PostgreSQL, 12+ assets, 2+ categories | `docker-compose.yml` + `seed_assets.py` (25 assets) |
| scikit-learn Random Forest, 5+ assets | `app/ml/maintenance.py` + `POST /maintenance/{id}/predict` |
| Automated alerts, 3+ assets | alert auto-created on predict |
| Gemini explanations, 3+ scenarios | `app/services/ai.py` |
| Groq health analysis, 3+ scenarios | `POST /maintenance/health-query` |
| 2 Power BI views | `/feeds/*` endpoints |
| pytest passing + docs | `tests/` + this README |

Prophet forecasting is Phase 2 (weeks 11+) and not required for midterm.

## Project layout

```
app/
  main.py            FastAPI app
  config.py          env/settings
  database.py        SQLAlchemy engine + session
  models/            ORM tables + Pydantic schemas
  routers/           assets, telemetry, maintenance, depreciation, feeds
  services/          depreciation math, AI (Gemini/Groq)
  ml/                scikit-learn maintenance model
simulator/           seed + telemetry simulator (Azure IoT Hub stand-in)
tests/               pytest suite (18 tests, 86% coverage)
sql/init.sql         schema (auto-loaded by Docker)
.github/workflows/   CI pipeline
```
