-- AssetPulse database schema
-- Runs automatically the first time the Docker container starts.

-- ---------- Asset master ----------
CREATE TABLE IF NOT EXISTS assets (
    asset_id        VARCHAR(20) PRIMARY KEY,          -- e.g. A-001
    name            VARCHAR(120) NOT NULL,
    category        VARCHAR(60)  NOT NULL,            -- Computing Hardware, Server & Networking, ...
    manufacturer    VARCHAR(80),
    model           VARCHAR(80),
    purchase_date   DATE         NOT NULL,
    purchase_price  NUMERIC(12,2) NOT NULL,
    useful_life_yrs INT          NOT NULL DEFAULT 5,
    depr_method     VARCHAR(30)  NOT NULL DEFAULT 'straight_line', -- or 'diminishing_balance'
    is_iot_enabled  BOOLEAN      NOT NULL DEFAULT FALSE,
    location        VARCHAR(120),
    assigned_to     VARCHAR(120),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------- Telemetry log ----------
CREATE TABLE IF NOT EXISTS telemetry (
    id              BIGSERIAL PRIMARY KEY,
    asset_id        VARCHAR(20) NOT NULL REFERENCES assets(asset_id),
    ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
    temperature_c   NUMERIC(6,2),
    utilisation_pct NUMERIC(6,2),
    fault_code      INT DEFAULT 0,
    battery_pct     NUMERIC(6,2),
    uptime_hours    NUMERIC(10,2)
);
CREATE INDEX IF NOT EXISTS idx_telemetry_asset_ts ON telemetry(asset_id, ts);

-- ---------- Maintenance predictions / alerts ----------
CREATE TABLE IF NOT EXISTS maintenance_alerts (
    id                  BIGSERIAL PRIMARY KEY,
    asset_id            VARCHAR(20) NOT NULL REFERENCES assets(asset_id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    urgency             VARCHAR(10)  NOT NULL,        -- Low / Medium / High
    predicted_days      INT,                          -- remaining useful life estimate
    confidence          NUMERIC(5,4),
    key_features        JSONB,                        -- telemetry features that drove the prediction
    gemini_explanation  TEXT                          -- plain-English explanation (nullable until generated)
);
CREATE INDEX IF NOT EXISTS idx_alert_asset ON maintenance_alerts(asset_id);

-- ---------- Depreciation snapshots ----------
CREATE TABLE IF NOT EXISTS depreciation (
    id                  BIGSERIAL PRIMARY KEY,
    asset_id            VARCHAR(20) NOT NULL REFERENCES assets(asset_id),
    as_of_date          DATE        NOT NULL,
    method              VARCHAR(30) NOT NULL,
    accumulated_depr    NUMERIC(12,2) NOT NULL,
    net_book_value      NUMERIC(12,2) NOT NULL,
    UNIQUE (asset_id, as_of_date, method)
);

-- ---------- Prophet forecast outputs ----------
CREATE TABLE IF NOT EXISTS forecasts (
    id            BIGSERIAL PRIMARY KEY,
    asset_id      VARCHAR(20) NOT NULL REFERENCES assets(asset_id),
    forecast_type VARCHAR(30) NOT NULL,               -- 'maintenance' or 'depreciation'
    ds            DATE        NOT NULL,                -- forecast date
    yhat          NUMERIC(14,4),
    yhat_lower    NUMERIC(14,4),
    yhat_upper    NUMERIC(14,4),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
