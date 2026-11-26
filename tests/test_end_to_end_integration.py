from __future__ import annotations

import os
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

# Add project roots to sys.path with weather_pipeline taking precedence for 'app'
PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEATHER_PATH = PROJECT_ROOT / "weather_pipeline"
ML_PATH = PROJECT_ROOT / "ml_model_v2"
RAG_PATH = PROJECT_ROOT / "rag_pipeline"

for p in (PROJECT_ROOT, ML_PATH, RAG_PATH, WEATHER_PATH):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class AtmoSyncEndToEndIntegrationTests(unittest.TestCase):
    """
    Comprehensive End-to-End integration test suite verifying the interaction
    between weather pipeline, ML forecasting, anomaly engine, RAG retrieval,
    and LLM synthesis.
    """

    def test_01_canonical_chunk_schema_reconciliation(self):
        """Verify that RetrievedChunk resolves both 'text' and 'content' without data loss."""
        from src.rag.schemas import RetrievedChunk

        # Case A: Supplied with 'text'
        chunk_a = RetrievedChunk(
            document_id="doc1",
            document_name="doc1.pdf",
            source="doc1.pdf",
            chunk_id="c1",
            text="Precipitation extremes in Montreal.",
        )
        self.assertEqual(chunk_a.text, "Precipitation extremes in Montreal.")
        self.assertEqual(chunk_a.content, "Precipitation extremes in Montreal.")
        self.assertEqual(chunk_a.char_count, len("Precipitation extremes in Montreal."))

        # Case B: Supplied with legacy 'content'
        chunk_b = RetrievedChunk.model_validate({
            "document_id": "doc2",
            "document_name": "doc2.pdf",
            "source": "doc2.pdf",
            "chunk_id": "c2",
            "content": "Coastal temperature trends in Vancouver.",
        })
        self.assertEqual(chunk_b.text, "Coastal temperature trends in Vancouver.")
        self.assertEqual(chunk_b.content, "Coastal temperature trends in Vancouver.")

    def test_02_weather_report_generation_and_metadata(self):
        """Verify deterministic naming and companion metadata for 7-day reports."""
        from app.config.locations import WEATHER_STATIONS
        from app.models.weather import WeatherObservation
        from app.services.report import (
            generate_weekly_report,
            save_weekly_report,
            get_report_filename,
        )

        start = date(2026, 11, 1)
        end = date(2026, 11, 7)
        filename = get_report_filename(start, end)
        self.assertEqual(filename, "weather_report_2026-11-01_2026-11-07.pdf")

        # Create sample observations for 9 stations
        obs = [
            WeatherObservation(
                climate_identifier=st.climate_identifier,
                observation_date=start,
                mean_temperature=5.2,
                min_temperature=1.0,
                max_temperature=9.4,
                total_precipitation=0.5,
            )
            for st in WEATHER_STATIONS
        ]

        pdf_bytes = generate_weekly_report(
            observations=obs,
            start_date=start,
            end_date=end,
            stations=WEATHER_STATIONS,
        )
        self.assertGreater(len(pdf_bytes), 1000)

        saved_path, meta = save_weekly_report(
            pdf_bytes=pdf_bytes,
            start_date=start,
            end_date=end,
            stations=WEATHER_STATIONS,
        )
        self.assertTrue(saved_path.exists())
        self.assertIn("sha256", meta)
        self.assertEqual(len(meta["stations"]), len(WEATHER_STATIONS))

    def test_03_ml_inference_and_consistency(self):
        """Verify LightGBM inference output ordering and physical constraints."""
        from forecasting.forecast_storage import get_forecast_rows

        # Fetch stored forecasts generated during pipeline validation
        rows = get_forecast_rows(station="toronto", limit=7)
        self.assertGreater(len(rows), 0, "Forecast rows must exist in storage")

        for r in rows:
            min_t = r["min_temp_c"]
            mean_t = r["mean_temp_c"]
            max_t = r["max_temp_c"]
            precip = r["precip_mm"]

            self.assertIsNotNone(min_t)
            self.assertIsNotNone(mean_t)
            self.assertIsNotNone(max_t)
            self.assertIsNotNone(precip)

            # Thermodynamic order check
            self.assertLessEqual(min_t, mean_t + 1e-4)
            self.assertLessEqual(mean_t, max_t + 1e-4)
            self.assertGreaterEqual(precip, 0.0)

    def test_04_anomaly_detector_baseline_scoring(self):
        """Verify anomaly detector z-score calculations and classification labels."""
        from forecasting.anomaly_detector import ClimateAnomalyDetector

        detector = ClimateAnomalyDetector()

        # Simulated warm temperature anomaly in Toronto in November
        sample_preds = [
            {
                "station": "toronto",
                "station_id": "6158355",
                "forecast_date": "2026-11-26",
                "min_temp_c": 12.0,
                "mean_temp_c": 18.0,  # Normal Nov mean is ~3.5°C
                "max_temp_c": 24.0,
                "precip_mm": 0.0,
            }
        ]

        anomalies = detector.scan_forecast_anomalies(sample_preds)
        self.assertGreater(len(anomalies), 0)

        top_anom = anomalies[0]
        self.assertEqual(top_anom.status, "anomaly")
        self.assertIn(top_anom.label, ("warm_anomaly", "extreme_heat"))
        self.assertGreater(top_anom.anomaly_score, 2.0)

    def test_05_idempotent_pdf_ingestion(self):
        """Verify that re-indexing identical PDFs reports already_indexed without duplicates."""
        from src.rag.ingestion.auto_ingest import ingest_pdf_document

        report_path = PROJECT_ROOT / "weather_pipeline" / "data" / "reports" / "weather_report_2026-10-01_2026-10-07.pdf"
        if report_path.exists():
            res = ingest_pdf_document(report_path, doc_type="weather_report", force=False)
            self.assertEqual(res.get("status"), "already_indexed")
            self.assertEqual(res.get("points_indexed"), 0)

    def test_06_structured_context_builder(self):
        """Verify unified structured context partitions ML and RAG information."""
        from src.llm.context.structured_context import build_structured_context

        ctx = build_structured_context(
            query="What is the forecast and climate pattern in Toronto?",
            station=None,  # Should auto-detect Toronto
            top_k=3,
        )

        self.assertEqual(ctx.detected_station, "toronto")
        self.assertTrue(ctx.ml_available)
        self.assertGreater(len(ctx.ml_forecasts), 0)
        self.assertIn("score_threshold", ctx.meta)

    def test_07_provider_agnostic_llm_layer(self):
        """Verify MockProvider outputs deterministic structured scientific answers."""
        from src.llm.clients.mock_provider import MockProvider

        provider = MockProvider()
        test_prompt = """
USER QUERY:
What is the outlook for Vancouver?

ML CONTEXT:
Station: Vancouver
7-Day Numerical Forecast:
| Date | Min Temp (°C) | Mean Temp (°C) | Max Temp (°C) | Precip (mm) |
| 2026-11-26 | 5.2 | 8.1 | 11.0 | 4.2 |

RETRIEVED RAG EVIDENCE:
--- Document [1]: weather_report_2026-10-01_2026-10-07.pdf (Page: 3, Score: 0.7489) ---
Vancouver Climate ID: 1108446 regional precipitation baselines.
"""
        response = provider.generate(test_prompt)
        self.assertIn("Vancouver", response)
        self.assertIn("LightGBM", response)
        self.assertIn("[weather_report_2026-10-01_2026-10-07.pdf, p. 3]", response)

    def test_08_end_to_end_ask_service(self):
        """Verify ClimateRAGService returns citations, groundedness, and confidence."""
        from src.llm.services.llm_service import create_climate_rag_service
        from src.llm.clients.mock_provider import MockProvider

        # Use mock provider for reproducible deterministic assertions
        service = create_climate_rag_service(provider=MockProvider())

        resp = service.explain_climate_event(
            user_query="Analyze precipitation and seasonal norms for Toronto",
            station="toronto",
            top_k=3,
        )

        self.assertIsNotNone(resp.answer)
        self.assertGreater(len(resp.answer), 50)
        self.assertIsInstance(resp.grounded, bool)
        self.assertIsInstance(resp.insufficient_evidence, bool)
        self.assertGreaterEqual(resp.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
