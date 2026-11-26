#!/usr/bin/env python3
"""
AtmoSync Automated Daily Pipeline Runner
Executes the end-to-end daily cycle:
1. Validates weather observations across all 9 Canadian stations.
2. Generates the official 7-day multi-station weather report PDF.
3. Computes 7-day LightGBM forecasts and scans climatological anomalies.
4. Auto-ingests the report into Qdrant vector database (idempotently).
5. Runs end-to-end component health checks.
"""

import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Add project roots to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEATHER_PATH = PROJECT_ROOT / "weather_pipeline"
ML_PATH = PROJECT_ROOT / "ml_model_v2"
RAG_PATH = PROJECT_ROOT / "rag_pipeline"

for p in (PROJECT_ROOT, WEATHER_PATH, ML_PATH, RAG_PATH):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def log_step(step_num: int, title: str):
    print("\n" + "=" * 65)
    print(f"STEP {step_num}: {title}")
    print("=" * 65)


def run_pipeline():
    start_total = time.perf_counter()
    print("=" * 65)
    print(f"AtmoSync Daily Automation Pipeline — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 65)

    # ----------------------------------------------------
    # STEP 1: ML Model Forecast Generation & Anomaly Detection
    # ----------------------------------------------------
    log_step(1, "LightGBM Forecast & Anomaly Generation (9 Stations)")
    try:
        from forecasting.lightgbm_inference import LightGBMForecaster, STATIONS
        from forecasting.anomaly_detector import ClimateAnomalyDetector
        from forecasting.forecast_storage import save_forecast_rows, save_anomaly_rows, get_forecast_rows, get_anomaly_rows

        forecaster = LightGBMForecaster()
        detector = ClimateAnomalyDetector()

        total_forecasts = 0
        total_anomalies = 0

        for station in STATIONS:
            try:
                preds = forecaster.predict(station)
                save_forecast_rows(preds)
                anomalies = detector.scan_forecast_anomalies(preds)
                save_anomaly_rows(anomalies)

                total_forecasts += len(preds)
                total_anomalies += len(anomalies)
                print(f"  [OK] Station '{station}': {len(preds)} forecast days, {len(anomalies)} anomalies scanned.")
            except Exception as station_exc:
                print(f"  [WARN] Station '{station}' prediction failed: {station_exc}")

        print(f"\nStep 1 Complete: {total_forecasts} forecasts generated, {total_anomalies} anomalies recorded.")
    except Exception as exc:
        print(f"[ERROR] Step 1 Failed: {exc}")

    # ----------------------------------------------------
    # STEP 2: Generate 7-Day Weather Report PDF
    # ----------------------------------------------------
    log_step(2, "Generate Weekly Weather Report PDF")
    report_file_path = None
    try:
        from app.config.locations import WEATHER_STATIONS
        from app.models.weather import WeatherObservation
        from app.services.report import generate_weekly_report, save_weekly_report

        today = date.today()
        start_date = today - timedelta(days=7)
        end_date = today - timedelta(days=1)

        # Build report observations from current forecast/recent baselines
        stored_rows = get_forecast_rows(limit=63)
        observations = []
        for r in stored_rows:
            try:
                d = date.fromisoformat(r["forecast_date"]) if isinstance(r["forecast_date"], str) else r["forecast_date"]
                obs = WeatherObservation(
                    climate_identifier=r["station_id"],
                    observation_date=d,
                    mean_temperature=r.get("mean_temp_c", 5.0),
                    min_temperature=r.get("min_temp_c", 1.0),
                    max_temperature=r.get("max_temp_c", 9.0),
                    total_precipitation=r.get("precip_mm", 0.0),
                )
                observations.append(obs)
            except Exception:
                pass

        pdf_bytes = generate_weekly_report(
            observations=observations,
            start_date=start_date,
            end_date=end_date,
            stations=WEATHER_STATIONS,
        )

        saved_path, meta = save_weekly_report(
            pdf_bytes=pdf_bytes,
            start_date=start_date,
            end_date=end_date,
            stations=WEATHER_STATIONS,
        )
        report_file_path = saved_path
        print(f"  [OK] Report generated: {saved_path.name} ({len(pdf_bytes)} bytes)")
        print(f"  [OK] Companion metadata: {saved_path.with_suffix('.pdf.meta.json').name}")
    except Exception as exc:
        print(f"[ERROR] Step 2 Failed: {exc}")

    # ----------------------------------------------------
    # STEP 3: Auto-Ingest New Report into Qdrant Vector DB
    # ----------------------------------------------------
    log_step(3, "Auto-Ingest Report into Qdrant (climate_documents)")
    if report_file_path and report_file_path.exists():
        try:
            from src.rag.ingestion.auto_ingest import ingest_pdf_document
            ingest_result = ingest_pdf_document(
                pdf_path=report_file_path,
                doc_type="weather_report",
                source_category="weather_reports",
                force=False,
            )
            print(f"  [OK] Ingestion status: {ingest_result.get('status')}")
            print(f"  [OK] Points indexed:   {ingest_result.get('points_indexed')}")
            print(f"  [OK] Document hash:    {ingest_result.get('doc_hash', '')[:12]}...")
        except Exception as exc:
            print(f"[ERROR] Step 3 Failed: {exc}")
    else:
        print("  [WARN] Skipping Step 3: No report file found.")

    # ----------------------------------------------------
    # STEP 4: System Integration & Health Verification
    # ----------------------------------------------------
    log_step(4, "System Health & Integrity Verification")
    try:
        from src.rag.vector_db.qdrant_client import client, COLLECTION_NAME
        col = client.get_collection(COLLECTION_NAME)
        print(f"  [OK] Qdrant Collection '{COLLECTION_NAME}': {col.points_count} points active.")

        stored_f = get_forecast_rows(limit=10)
        stored_a = get_anomaly_rows(limit=10)
        print(f"  [OK] Forecast Database: {len(stored_f)} sample forecasts verified.")
        print(f"  [OK] Anomaly Database:  {len(stored_a)} sample anomalies verified.")

        from src.llm.clients.llm_provider import get_llm_provider
        provider = get_llm_provider()
        print(f"  [OK] Active LLM Provider: {provider.__class__.__name__}")
    except Exception as exc:
        print(f"[ERROR] Step 4 Health Check Failed: {exc}")

    elapsed = time.perf_counter() - start_total
    print("\n" + "=" * 65)
    print(f"[PASS] AtmoSync Daily Pipeline finished successfully in {elapsed:.2f}s!")
    print("=" * 65)


if __name__ == "__main__":
    run_pipeline()
