# AtmoSync ML API Contract (v1.0.0)

This document specifies the frozen interface contract for the Machine Learning and Anomaly Detection service in **AtmoSync v2.0** (`ml_model_v2`).

## 1. Overview & Capabilities

- **Model Engine**: LightGBM Multi-Output Regressor (`models/Light_GBM/lightgbm_models.joblib`, 28 estimators across 7 horizon days and 4 target variables).
- **Target Variables**:
  - `min_temp_c` (°C)
  - `mean_temp_c` (°C)
  - `max_temp_c` (°C)
  - `precip_mm` (mm, non-negative)
- **Supported Stations**: 9 Canadian primary meteorological stations:
  - `vancouver` (`1108395`)
  - `edmonton` (`3012210`)
  - `calgary` (`3031094`)
  - `winnipeg` (`5023222`)
  - `ottawa` (`6106000`)
  - `toronto` (`6158355`)
  - `montreal` (`7025251`)
  - `quebec city` (`701S001`)
  - `halifax` (`8202251`)
- **Lookback Window**: 90 days historical daily weather data from ECCC API.
- **Forecast Horizon**: 7 forward calendar days.
- **Physical Consistency Guarantee**: $T_{min} \le T_{mean} \le T_{max}$ and $Precip \ge 0.0$.
- **Anomaly Detection Engine**: Station-level monthly climatological baselines derived from Environment Canada normal statistics, evaluated using rolling z-scores ($|z| \ge 2.0$ for warning/anomaly, $|z| \ge 3.0$ for extreme alert) and precipitation percentile checks.

---

## 2. Endpoints

### 2.1 GET `/forecasts`

Query stored 7-day forecasts.

- **Query Parameters**:
  - `station` (string, optional): station name (case-insensitive)
  - `start_date` (ISO date, optional): `YYYY-MM-DD`
  - `end_date` (ISO date, optional): `YYYY-MM-DD`
  - `limit` (integer, default 500, max 2000)
- **Response Model**:
```json
{
  "count": 7,
  "forecasts": [
    {
      "station": "toronto",
      "station_id": "6158355",
      "forecast_date": "2026-11-26",
      "min_temp_c": 1.25,
      "mean_temp_c": 4.12,
      "max_temp_c": 7.34,
      "precip_mm": 0.45,
      "model_name": "LightGBM",
      "model_version": "lightgbm-v1",
      "generated_at": "2026-11-26T05:12:16.000000+00:00"
    }
  ]
}
```

### 2.2 POST `/forecasts/predict`

Generate on-demand 7-day predictions and detect anomalies for a specific station.

- **Request Body**:
```json
{
  "station": "toronto",
  "end_date": "2026-11-25"
}
```
- **Response Model**:
```json
{
  "station": "toronto",
  "station_id": "6158355",
  "model_name": "LightGBM",
  "model_version": "lightgbm-v1",
  "count": 7,
  "forecasts": [...],
  "anomalies": [...]
}
```

### 2.3 GET `/anomalies`

Query detected climate anomalies from the database or cache.

- **Query Parameters**:
  - `station` (string, optional): filter by station name
  - `variable` (string, optional): e.g. `mean_temp_c`, `max_temp_c`, `precip_mm`
  - `status` (string, optional): `anomaly`, `warning`, `normal`
  - `start_date` (ISO date, optional)
  - `end_date` (ISO date, optional)
  - `limit` (integer, default 100)
- **Response Record Schema**:
```json
{
  "station": "quebec city",
  "station_id": "701S001",
  "variable": "mean_temp_c",
  "date": "2026-11-26",
  "value": 6.78,
  "expected_baseline": -0.3,
  "expected_range_min": -7.3,
  "expected_range_max": 6.7,
  "anomaly_score": 2.02,
  "threshold": 2.0,
  "status": "anomaly",
  "label": "warm_anomaly",
  "is_forecast": 1,
  "detected_at": "2026-11-26T05:12:16.759355+00:00"
}
```

---

## 3. Storage Architecture

Forecasts and anomalies are stored with a dual-persistence strategy:
1. **Primary Cloud**: Supabase PostgreSQL (`public.weather_forecasts` and `public.weather_anomalies`), when configured via `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
2. **Resilient Local Fallback**: SQLite (`ml_model_v2/data/forecast_cache.db`), automatically enabled when Supabase credentials are not present or during network isolation. This guarantees that `GET /forecasts` never fails with 503 or empty lists due to external outages.
