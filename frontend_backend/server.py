import os
import sys
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Add root, ml_model_v2, and rag_pipeline to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ML_PATH = PROJECT_ROOT / "ml_model_v2"
RAG_PATH = PROJECT_ROOT / "rag_pipeline"

for p in (PROJECT_ROOT, ML_PATH, RAG_PATH):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from src.llm.services.llm_service import create_climate_rag_service
from forecasting.forecast_storage import get_forecast_rows, get_anomaly_rows, save_forecast_rows, save_anomaly_rows
from forecasting.anomaly_detector import ClimateAnomalyDetector

app = Flask(__name__, static_folder="static")
CORS(app)

_rag_service = None
_anomaly_detector = ClimateAnomalyDetector()


def get_rag_service():
    global _rag_service
    if _rag_service is None:
        _rag_service = create_climate_rag_service()
    return _rag_service


# Monitored Canadian weather stations (matches weather_pipeline locations)
WEATHER_STATIONS = [
    {"city": "Toronto", "climate_identifier": "6158355", "province": "Ontario"},
    {"city": "Montreal", "climate_identifier": "7025251", "province": "Quebec"},
    {"city": "Vancouver", "climate_identifier": "1108395", "province": "British Columbia"},
    {"city": "Calgary", "climate_identifier": "3031094", "province": "Alberta"},
    {"city": "Edmonton", "climate_identifier": "3012210", "province": "Alberta"},
    {"city": "Ottawa", "climate_identifier": "6106000", "province": "Ontario"},
    {"city": "Winnipeg", "climate_identifier": "5023222", "province": "Manitoba"},
    {"city": "Quebec City", "climate_identifier": "701S001", "province": "Quebec"},
    {"city": "Halifax", "climate_identifier": "8202251", "province": "Nova Scotia"},
]


@app.route("/")
def index():
    """Serve the interactive dashboard."""
    return send_from_directory("static", "index.html")


@app.route("/vendor/<path:filename>")
def vendor_assets(filename):
    """Serve local vendor assets."""
    return send_from_directory("static/vendor", filename)


@app.route("/api/weather/stations", methods=["GET"])
def get_stations():
    """Return monitored Canadian weather stations."""
    return jsonify(WEATHER_STATIONS)


@app.route("/api/weather/forecast", methods=["GET"])
def get_forecast():
    """
    Return 7-day LightGBM weather forecasts and anomalies from ML storage.
    Automatically generates on-demand if not already cached.
    """
    station = request.args.get("station", "toronto").strip().lower()

    # 1. Fetch from ML storage
    rows = get_forecast_rows(station=station, limit=7)
    anomalies = get_anomaly_rows(station=station, limit=10)

    # 2. If storage is empty for this station, run on-demand LightGBM prediction
    if not rows:
        try:
            from forecasting.lightgbm_inference import LightGBMForecaster, STATIONS
            norm_st = station.replace("_", " ")
            if norm_st in STATIONS:
                forecaster = LightGBMForecaster()
                preds = forecaster.predict(norm_st)
                save_forecast_rows(preds)
                anom_scans = _anomaly_detector.scan_forecast_anomalies(preds)
                save_anomaly_rows(anom_scans)
                rows = get_forecast_rows(station=station, limit=7)
                anomalies = get_anomaly_rows(station=station, limit=10)
        except Exception as exc:
            app.logger.warning("On-demand forecast prediction failed: %s", exc)

    # 3. Format predictions for frontend compatibility (both naming conventions)
    predictions = []
    for r in rows:
        min_t = r.get("min_temp_c")
        mean_t = r.get("mean_temp_c")
        max_t = r.get("max_temp_c")
        precip = r.get("precip_mm")
        predictions.append({
            "forecast_date": r.get("forecast_date"),
            "min_temp_c": min_t,
            "mean_temp_c": mean_t,
            "max_temp_c": max_t,
            "precip_mm": precip,
            # Frontend chart compatibility aliases
            "predicted_min_temp_c": min_t,
            "predicted_mean_temp_c": mean_t,
            "predicted_max_temp_c": max_t,
            "predicted_precip_mm": precip,
        })

    return jsonify({
        "station": station,
        "model": "LightGBM",
        "model_version": "lightgbm-v1",
        "forecast_horizon_days": 7,
        "predictions": predictions,
        "forecasts": predictions,
        "anomalies": anomalies,
    })


@app.route("/api/weather/anomalies", methods=["GET"])
def get_anomalies_route():
    """Query detected anomalies for a specific station."""
    station = request.args.get("station")
    rows = get_anomaly_rows(station=station, limit=50)
    return jsonify({
        "station": station,
        "count": len(rows),
        "anomalies": rows,
    })


@app.route("/api/ask", methods=["POST"])
@app.route("/api/rag/explain", methods=["POST"])
def explain_climate():
    """
    Unified multimodal climate intelligence endpoint.
    Retrieves literature from Qdrant, incorporates LightGBM 7-day forecast & anomalies,
    and returns a cited, scientifically validated explanation.
    """
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    station = data.get("station")
    ml_forecast = data.get("ml_forecast")
    top_k = int(data.get("top_k", 5))

    if not query:
        return jsonify({"error": "Query cannot be empty."}), 400

    try:
        service = get_rag_service()

        result = service.explain_climate_event(
            user_query=query,
            ml_context=ml_forecast,
            station=station,
            top_k=top_k,
        )

        return jsonify({
            "answer": result.answer,
            "citations": [
                {
                    "source": c.source,
                    "page": c.page,
                    "chunk_id": c.chunk_id,
                }
                for c in result.citation
            ],
            "grounded": result.grounded,
            "insufficient_evidence": result.insufficient_evidence,
            "confidence": result.confidence,
            "event_summary": {
                "event_type": result.event_summary.event_type if result.event_summary else None,
                "severity": result.event_summary.severity if result.event_summary else None,
            } if result.event_summary else None,
        })
    except Exception as exc:
        app.logger.exception("Error during /api/ask generation: %s", exc)
        return jsonify({
            "error": str(exc),
            "answer": f"Unable to generate response due to service error: {exc}",
            "citations": [],
            "grounded": False,
            "insufficient_evidence": True,
        }), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "system": "AtmoSync v2.0 Unified Gateway",
        "modules": ["weather_pipeline", "ml_model_v2", "rag_pipeline"],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=" * 60)
    print(f"Starting AtmoSync Dashboard & API on http://localhost:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
