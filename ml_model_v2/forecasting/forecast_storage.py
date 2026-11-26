"""
Local and Staging Forecast Storage Module.

Provides resilient SQLite storage for weather forecasts and detected anomalies,
ensuring AtmoSync functions smoothly offline, locally, or as a cache alongside Supabase.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
from typing import Any, Sequence

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = Path(
    os.getenv("ATMOSYNC_LOCAL_DB", PROJECT_ROOT / "data" / "atmosync.db")
)


def get_db_connection(db_path: Path | None = None) -> sqlite3.Connection:
    target = db_path or DEFAULT_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    return conn


def init_storage(db_path: Path | None = None) -> None:
    """Initialize SQLite schema for forecasts and anomalies."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station TEXT NOT NULL,
                station_id TEXT NOT NULL,
                history_start TEXT NOT NULL,
                history_end TEXT NOT NULL,
                forecast_date TEXT NOT NULL,
                forecast_horizon_day INTEGER NOT NULL,
                model_name TEXT NOT NULL DEFAULT 'LightGBM',
                model_version TEXT NOT NULL DEFAULT 'lightgbm-v1',
                max_temp_c REAL,
                min_temp_c REAL,
                mean_temp_c REAL,
                precip_mm REAL,
                generated_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(station, forecast_date)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station TEXT NOT NULL,
                station_id TEXT NOT NULL,
                variable TEXT NOT NULL,
                date TEXT NOT NULL,
                value REAL NOT NULL,
                expected_baseline REAL NOT NULL,
                expected_range_min REAL NOT NULL,
                expected_range_max REAL NOT NULL,
                anomaly_score REAL NOT NULL,
                threshold REAL NOT NULL,
                status TEXT NOT NULL,
                label TEXT NOT NULL,
                is_forecast INTEGER NOT NULL DEFAULT 1,
                detected_at TEXT NOT NULL,
                UNIQUE(station, variable, date)
            )
            """
        )
        conn.commit()


def save_forecast_rows(
    rows: Sequence[dict[str, Any]],
    db_path: Path | None = None,
) -> int:
    """Upsert forecast rows into the local database."""
    init_storage(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    inserted = 0

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        for row in rows:
            station = str(row.get("station", "")).strip().lower()
            station_id = str(row.get("station_id", ""))
            f_date = str(row.get("forecast_date", ""))
            if not station or not f_date:
                continue

            history_start = str(row.get("history_start", ""))
            history_end = str(row.get("history_end", ""))
            horizon = int(row.get("forecast_horizon_day", 1))

            max_temp = row.get("max_temp_c")
            if max_temp is None:
                max_temp = row.get("predicted_max_temp_c")

            min_temp = row.get("min_temp_c")
            if min_temp is None:
                min_temp = row.get("predicted_min_temp_c")

            mean_temp = row.get("mean_temp_c")
            if mean_temp is None:
                mean_temp = row.get("predicted_mean_temp_c")

            precip = row.get("precip_mm")
            if precip is None:
                precip = row.get("predicted_precip_mm")

            model_name = str(row.get("model_name") or row.get("model") or "LightGBM")
            model_ver = str(row.get("model_version") or "lightgbm-v1")
            gen_at = str(row.get("generated_at") or now_iso)

            cursor.execute(
                """
                INSERT INTO weather_forecasts (
                    station, station_id, history_start, history_end,
                    forecast_date, forecast_horizon_day, model_name, model_version,
                    max_temp_c, min_temp_c, mean_temp_c, precip_mm,
                    generated_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(station, forecast_date) DO UPDATE SET
                    max_temp_c=excluded.max_temp_c,
                    min_temp_c=excluded.min_temp_c,
                    mean_temp_c=excluded.mean_temp_c,
                    precip_mm=excluded.precip_mm,
                    generated_at=excluded.generated_at,
                    updated_at=excluded.updated_at
                """,
                (
                    station, station_id, history_start, history_end,
                    f_date, horizon, model_name, model_ver,
                    float(max_temp) if max_temp is not None else None,
                    float(min_temp) if min_temp is not None else None,
                    float(mean_temp) if mean_temp is not None else None,
                    float(precip) if precip is not None else None,
                    gen_at, now_iso, now_iso,
                ),
            )
            inserted += 1
        conn.commit()

    return inserted


def get_forecast_rows(
    station: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Retrieve saved forecasts from local storage."""
    init_storage(db_path)
    query = "SELECT * FROM weather_forecasts WHERE 1=1"
    params: list[Any] = []

    if station:
        norm_station = station.strip().lower().replace("_", " ")
        query += " AND (station = ? OR station = ?)"
        params.extend([norm_station, norm_station.replace(" ", "_")])

    if start_date:
        query += " AND forecast_date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND forecast_date <= ?"
        params.append(end_date)

    query += " ORDER BY forecast_date ASC LIMIT ?"
    params.append(limit)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]

    return rows


def save_anomaly_rows(
    anomalies: Sequence[Any],
    db_path: Path | None = None,
) -> int:
    """Save detected anomaly results."""
    init_storage(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    inserted = 0

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        for item in anomalies:
            d = item.to_dict() if hasattr(item, "to_dict") else item
            cursor.execute(
                """
                INSERT INTO weather_anomalies (
                    station, station_id, variable, date, value,
                    expected_baseline, expected_range_min, expected_range_max,
                    anomaly_score, threshold, status, label, is_forecast, detected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(station, variable, date) DO UPDATE SET
                    value=excluded.value,
                    expected_baseline=excluded.expected_baseline,
                    expected_range_min=excluded.expected_range_min,
                    expected_range_max=excluded.expected_range_max,
                    anomaly_score=excluded.anomaly_score,
                    status=excluded.status,
                    label=excluded.label,
                    detected_at=excluded.detected_at
                """,
                (
                    d["station"],
                    d["station_id"],
                    d["variable"],
                    d["date"],
                    d["value"],
                    d["expected_baseline"],
                    d["expected_range"][0],
                    d["expected_range"][1],
                    d["anomaly_score"],
                    d["threshold"],
                    d["status"],
                    d["label"],
                    1 if d.get("is_forecast", True) else 0,
                    now_iso,
                ),
            )
            inserted += 1
        conn.commit()

    return inserted


def get_anomaly_rows(
    station: str | None = None,
    status: str | None = None,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Retrieve anomalies from local storage."""
    init_storage(db_path)
    query = "SELECT * FROM weather_anomalies WHERE 1=1"
    params: list[Any] = []

    if station:
        norm_station = station.strip().lower().replace("_", " ")
        query += " AND (station = ? OR station = ?)"
        params.extend([norm_station, norm_station.replace(" ", "_")])

    if status:
        query += " AND status = ?"
        params.append(status.strip().lower())

    query += " ORDER BY date ASC, anomaly_score DESC LIMIT ?"
    params.append(limit)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]

    return rows
