import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests

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
from frontend_backend.calendar_weather import fetch_eccc_observations
from frontend_backend.current_weather import (
    fetch_current_weather,
    fetch_daily_forecast,
    get_station_timezone,
)
from frontend_backend.weather_calendar import calendar_date_mode

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
    return send_from_directory(app.static_folder, "index.html")


@app.route("/vendor/<path:filename>")
def vendor_assets(filename):
    """Serve local vendor assets."""
    return send_from_directory(Path(app.static_folder) / "vendor", filename)


@app.route("/api/weather/stations", methods=["GET"])
def get_stations():
    """Return monitored Canadian weather stations."""
    return jsonify(WEATHER_STATIONS)


@app.route("/api/weather/current", methods=["GET"])
def get_current_weather():
    """Return current Open-Meteo weather data for a monitored station."""
    station_name = request.args.get("station", "toronto").strip().casefold()
    station = next(
        (
            item
            for item in WEATHER_STATIONS
            if item["city"].casefold() == station_name
        ),
        None,
    )
    if station is None:
        return jsonify({"error": f"Unknown weather station: {station_name}"}), 404

    try:
        current_weather = fetch_current_weather(station["city"])
    except (requests.RequestException, ValueError):
        app.logger.exception(
            "Failed to fetch current weather for %s",
            station["city"],
        )
        return jsonify({"error": "Unable to fetch current weather."}), 502

    current_weather["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    return jsonify(current_weather)


def _get_station_forecast_for_date(
    station: str,
    target_date: date,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    rows = get_forecast_rows(
        station=station,
        start_date=target_date.isoformat(),
        end_date=target_date.isoformat(),
        limit=1,
    )
    if not rows:
        from forecasting.lightgbm_inference import LightGBMForecaster, STATIONS

        normalized_station = station.strip().casefold().replace("_", " ")
        if normalized_station not in STATIONS:
            return None, []
        predictions = LightGBMForecaster().predict(
            normalized_station,
            end_date=target_date - timedelta(days=1),
        )
        save_forecast_rows(predictions)
        save_anomaly_rows(_anomaly_detector.scan_forecast_anomalies(predictions))
        rows = get_forecast_rows(
            station=station,
            start_date=target_date.isoformat(),
            end_date=target_date.isoformat(),
            limit=1,
        )

    if not rows:
        return None, []

    anomalies = [
        anomaly
        for anomaly in get_anomaly_rows(station=station, limit=1000)
        if anomaly.get("date") == target_date.isoformat()
        and bool(anomaly.get("is_forecast"))
    ]
    return rows[0], anomalies


@app.route("/api/weather/calendar", methods=["GET"])
def get_calendar_weather():
    """Return date-scoped current, observed, or forecast weather."""
    station_name = request.args.get("station", "toronto").strip().casefold()
    station = next(
        (
            item
            for item in WEATHER_STATIONS
            if item["city"].casefold() == station_name
        ),
        None,
    )
    if station is None:
        return jsonify({"error": f"Unknown weather station: {station_name}"}), 404

    try:
        raw_date = request.args.get("date", "")
        selected_date = date.fromisoformat(raw_date)
        if selected_date.isoformat() != raw_date:
            raise ValueError("Date must use YYYY-MM-DD format.")
    except ValueError:
        return jsonify({"error": "A valid YYYY-MM-DD date is required."}), 400

    try:
        timezone_name = get_station_timezone(station["city"])
        mode, local_today, max_forecast_date = calendar_date_mode(
            selected_date,
            timezone_name,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    base_url = (
        os.getenv("ATMOSYNC_OBSERVATIONS_API_BASE_URL")
        or os.getenv("ATMOSYNC_WEATHER_API_BASE_URL")
        or "https://atmosyncv2-0.onrender.com"
    )
    result: dict[str, Any] = {
        "station": station["city"],
        "date": selected_date.isoformat(),
        "mode": mode,
        "timezone": timezone_name,
        "local_today": local_today.isoformat(),
        "max_forecast_date": max_forecast_date.isoformat(),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "eccc_observations": [],
        "provider_forecast": None,
        "ml_forecast": None,
        "anomalies": [],
    }

    if mode in ("historical", "current"):
        try:
            result["eccc_observations"] = fetch_eccc_observations(
                base_url,
                station["city"],
                selected_date,
            )
        except (requests.RequestException, ValueError):
            app.logger.exception(
                "Failed to fetch ECCC observations for %s on %s",
                station["city"],
                selected_date,
            )
            if mode == "historical":
                return jsonify({
                    "error": "Unable to fetch ECCC observations for this date.",
                }), 502
            result["eccc_error"] = (
                "ECCC observations are unavailable; current weather may still load."
            )

    if mode == "current":
        try:
            result["current_weather"] = fetch_current_weather(station["city"])
            result["current_weather"]["retrieved_at"] = datetime.now(
                timezone.utc
            ).isoformat()
        except (requests.RequestException, ValueError):
            app.logger.exception(
                "Failed to fetch current weather for %s",
                station["city"],
            )
            return jsonify({"error": "Unable to fetch current weather."}), 502

    if mode == "forecast":
        try:
            result["provider_forecast"] = fetch_daily_forecast(
                station["city"],
                selected_date,
            )
        except (requests.RequestException, ValueError):
            app.logger.exception(
                "Failed to fetch provider forecast for %s on %s",
                station["city"],
                selected_date,
            )
            result["provider_error"] = "Open-Meteo forecast is unavailable."

        try:
            forecast, anomalies = _get_station_forecast_for_date(
                station_name,
                selected_date,
            )
            result["ml_forecast"] = forecast
            result["anomalies"] = anomalies
        except Exception:
            app.logger.exception(
                "Failed to fetch LightGBM forecast for %s on %s",
                station["city"],
                selected_date,
            )
            result["ml_error"] = "LightGBM prediction is unavailable."

        if (
            result["provider_forecast"] is None
            and result["ml_forecast"] is None
            and "provider_error" in result
            and "ml_error" in result
        ):
            return jsonify({
                **result,
                "error": "No forecast source is available for this date.",
            }), 502

    return jsonify(result)


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

    generated_at_values = [r.get("generated_at") for r in rows if r.get("generated_at")]
    return jsonify({
        "station": station,
        "model": "LightGBM",
        "model_version": "lightgbm-v1",
        "generated_at": max(generated_at_values) if generated_at_values else None,
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
