import os
import sys
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Add root and rag_pipeline to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAG_PATH = PROJECT_ROOT / "rag_pipeline"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(RAG_PATH) not in sys.path:
    sys.path.insert(0, str(RAG_PATH))

from src.llm.services.llm_service import create_climate_rag_service

app = Flask(__name__, static_folder="static")
CORS(app)

# Lazy-loaded RAG service
_rag_service = None


def get_rag_service():
    global _rag_service
    if _rag_service is None:
        _rag_service = create_climate_rag_service()
    return _rag_service


# Monitored Canadian weather stations (matches weather_pipeline locations)
WEATHER_STATIONS = [
    {"city": "Toronto", "climate_identifier": "6158355", "province": "Ontario"},
    {"city": "Montreal", "climate_identifier": "7014160", "province": "Quebec"},
    {"city": "Vancouver", "climate_identifier": "1108446", "province": "British Columbia"},
    {"city": "Calgary", "climate_identifier": "3031094", "province": "Alberta"},
    {"city": "Edmonton", "climate_identifier": "3012209", "province": "Alberta"},
    {"city": "Ottawa", "climate_identifier": "6105978", "province": "Ontario"},
    {"city": "Winnipeg", "climate_identifier": "502S001", "province": "Manitoba"},
    {"city": "Quebec City", "climate_identifier": "701S001", "province": "Quebec"},
    {"city": "Halifax", "climate_identifier": "8202251", "province": "Nova Scotia"},
]

# Baseline forecast data matching the LightGBM ML model contract
MOCK_FORECASTS = {
    "toronto": {
        "station": "toronto",
        "model": "LightGBM",
        "model_version": "2.0",
        "forecast_horizon_days": 7,
        "predictions": [
            {"forecast_date": "2026-11-19", "predicted_min_temp_c": 3.2, "predicted_mean_temp_c": 7.4, "predicted_max_temp_c": 11.6, "predicted_precip_mm": 0.0},
            {"forecast_date": "2026-11-20", "predicted_min_temp_c": 4.1, "predicted_mean_temp_c": 8.0, "predicted_max_temp_c": 12.2, "predicted_precip_mm": 1.2},
            {"forecast_date": "2026-11-21", "predicted_min_temp_c": 2.5, "predicted_mean_temp_c": 6.8, "predicted_max_temp_c": 10.5, "predicted_precip_mm": 4.5},
            {"forecast_date": "2026-11-22", "predicted_min_temp_c": 1.0, "predicted_mean_temp_c": 4.5, "predicted_max_temp_c": 8.1, "predicted_precip_mm": 0.0},
            {"forecast_date": "2026-11-23", "predicted_min_temp_c": -0.5, "predicted_mean_temp_c": 3.2, "predicted_max_temp_c": 6.8, "predicted_precip_mm": 0.2},
            {"forecast_date": "2026-11-24", "predicted_min_temp_c": 0.8, "predicted_mean_temp_c": 4.9, "predicted_max_temp_c": 9.0, "predicted_precip_mm": 0.0},
            {"forecast_date": "2026-11-25", "predicted_min_temp_c": 2.0, "predicted_mean_temp_c": 5.8, "predicted_max_temp_c": 9.5, "predicted_precip_mm": 0.0},
        ],
    },
    "vancouver": {
        "station": "vancouver",
        "model": "LightGBM",
        "model_version": "2.0",
        "forecast_horizon_days": 7,
        "predictions": [
            {"forecast_date": "2026-11-19", "predicted_min_temp_c": 7.5, "predicted_mean_temp_c": 10.2, "predicted_max_temp_c": 13.1, "predicted_precip_mm": 8.5},
            {"forecast_date": "2026-11-20", "predicted_min_temp_c": 8.0, "predicted_mean_temp_c": 11.0, "predicted_max_temp_c": 14.0, "predicted_precip_mm": 12.0},
            {"forecast_date": "2026-11-21", "predicted_min_temp_c": 6.8, "predicted_mean_temp_c": 9.5, "predicted_max_temp_c": 12.2, "predicted_precip_mm": 5.4},
            {"forecast_date": "2026-11-22", "predicted_min_temp_c": 5.5, "predicted_mean_temp_c": 8.2, "predicted_max_temp_c": 11.0, "predicted_precip_mm": 2.1},
            {"forecast_date": "2026-11-23", "predicted_min_temp_c": 6.2, "predicted_mean_temp_c": 9.0, "predicted_max_temp_c": 11.8, "predicted_precip_mm": 6.7},
            {"forecast_date": "2026-11-24", "predicted_min_temp_c": 7.0, "predicted_mean_temp_c": 9.8, "predicted_max_temp_c": 12.5, "predicted_precip_mm": 10.2},
            {"forecast_date": "2026-11-25", "predicted_min_temp_c": 6.5, "predicted_mean_temp_c": 9.2, "predicted_max_temp_c": 12.0, "predicted_precip_mm": 4.0},
        ],
    },
    "calgary": {
        "station": "calgary",
        "model": "LightGBM",
        "model_version": "2.0",
        "forecast_horizon_days": 7,
        "predictions": [
            {"forecast_date": "2026-11-19", "predicted_min_temp_c": -2.0, "predicted_mean_temp_c": 3.0, "predicted_max_temp_c": 8.5, "predicted_precip_mm": 0.0},
            {"forecast_date": "2026-11-20", "predicted_min_temp_c": -1.5, "predicted_mean_temp_c": 4.2, "predicted_max_temp_c": 9.8, "predicted_precip_mm": 0.0},
            {"forecast_date": "2026-11-21", "predicted_min_temp_c": -4.0, "predicted_mean_temp_c": 1.5, "predicted_max_temp_c": 6.0, "predicted_precip_mm": 1.5},
            {"forecast_date": "2026-11-22", "predicted_min_temp_c": -6.5, "predicted_mean_temp_c": -1.2, "predicted_max_temp_c": 3.4, "predicted_precip_mm": 0.0},
            {"forecast_date": "2026-11-23", "predicted_min_temp_c": -5.0, "predicted_mean_temp_c": 0.5, "predicted_max_temp_c": 5.8, "predicted_precip_mm": 0.0},
            {"forecast_date": "2026-11-24", "predicted_min_temp_c": -3.2, "predicted_mean_temp_c": 2.1, "predicted_max_temp_c": 7.0, "predicted_precip_mm": 0.0},
            {"forecast_date": "2026-11-25", "predicted_min_temp_c": -2.0, "predicted_mean_temp_c": 3.5, "predicted_max_temp_c": 8.2, "predicted_precip_mm": 0.0},
        ],
    },
}


@app.route("/")
def index():
    """Serve the interactive dashboard."""
    return send_from_directory("static", "index.html")


@app.route("/api/weather/stations", methods=["GET"])
def get_stations():
    """Return monitored Canadian weather stations."""
    return jsonify(WEATHER_STATIONS)


@app.route("/api/weather/forecast", methods=["GET"])
def get_forecast():
    """
    Return 7-day LightGBM weather forecasts.
    Uses station parameter; falls back to default if unlisted.
    """
    station = request.args.get("station", "toronto").strip().casefold()

    if station in MOCK_FORECASTS:
        return jsonify(MOCK_FORECASTS[station])

    # Generate synthetic default for other stations
    default_station_name = station.capitalize()
    return jsonify({
        "station": station,
        "model": "LightGBM",
        "model_version": "2.0",
        "forecast_horizon_days": 7,
        "predictions": [
            {
                "forecast_date": f"2026-11-{19 + i}",
                "predicted_min_temp_c": round(1.0 + i * 0.5, 1),
                "predicted_mean_temp_c": round(5.0 + i * 0.4, 1),
                "predicted_max_temp_c": round(9.0 + i * 0.6, 1),
                "predicted_precip_mm": 0.5 if i % 2 == 0 else 0.0,
            }
            for i in range(7)
        ],
    })


@app.route("/api/rag/explain", methods=["POST"])
def explain_climate():
    """
    Generate an evidence-backed scientific climate explanation using Qdrant and Gemini.
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

        # If ml_forecast not provided directly, lookup by station
        if ml_forecast is None and station:
            normalized_station = station.strip().casefold()
            ml_forecast = MOCK_FORECASTS.get(normalized_station, {"station": station})

        result = service.explain_climate_event(
            user_query=query,
            ml_context=ml_forecast,
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
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "system": "AtmoSync v2.0 Unified Gateway",
        "modules": ["weather_pipeline", "ml_model", "rag_pipeline"],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=" * 60)
    print(f"Starting AtmoSync Dashboard & API on http://localhost:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
