from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"
CITY_COORDINATES = {
    "toronto": (43.6532, -79.3832),
    "montreal": (45.5019, -73.5674),
    "vancouver": (49.2827, -123.1207),
    "calgary": (51.0447, -114.0719),
    "edmonton": (53.5461, -113.4938),
    "ottawa": (45.4215, -75.6972),
    "winnipeg": (49.8951, -97.1384),
    "quebec city": (46.8139, -71.2080),
    "halifax": (44.6488, -63.5752),
}
CITY_TIMEZONES = {
    "toronto": "America/Toronto",
    "montreal": "America/Toronto",
    "vancouver": "America/Vancouver",
    "calgary": "America/Edmonton",
    "edmonton": "America/Edmonton",
    "ottawa": "America/Toronto",
    "winnipeg": "America/Winnipeg",
    "quebec city": "America/Toronto",
    "halifax": "America/Halifax",
}

WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def get_station_timezone(station: str) -> str:
    timezone_name = CITY_TIMEZONES.get(station.strip().casefold())
    if timezone_name is None:
        raise ValueError(f"No timezone configured for {station!r}.")
    return timezone_name


def fetch_current_weather(station: str) -> dict[str, Any]:
    normalized_station = station.strip().casefold()
    coordinates = CITY_COORDINATES.get(normalized_station)
    if coordinates is None:
        raise ValueError(f"No current-weather coordinates for {station!r}.")

    latitude, longitude = coordinates
    response = requests.get(
        OPEN_METEO_API_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,"
                "precipitation,rain,showers,snowfall,weather_code,cloud_cover,"
                "pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,"
                "wind_gusts_10m,visibility"
            ),
            "daily": (
                "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                "sunrise,sunset"
            ),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "timezone": "auto",
            "forecast_days": 1,
        },
        timeout=15,
    )
    response.raise_for_status()

    payload = response.json()
    current = payload.get("current") if isinstance(payload, dict) else None
    daily = payload.get("daily") if isinstance(payload, dict) else None
    if not isinstance(current, dict) or not isinstance(daily, dict):
        raise ValueError("Open-Meteo returned an invalid current-weather response.")

    def first_daily_value(name: str) -> Any:
        values = daily.get(name)
        return values[0] if isinstance(values, list) and values else None

    current_time = current.get("time")
    current_time_utc = None
    if isinstance(current_time, str):
        source_time = datetime.fromisoformat(current_time)
        if source_time.tzinfo is None and isinstance(
            payload.get("utc_offset_seconds"), int
        ):
            source_time = source_time.replace(
                tzinfo=timezone(
                    timedelta(seconds=payload["utc_offset_seconds"])
                )
            )
        if source_time.tzinfo is not None:
            current_time_utc = source_time.astimezone(timezone.utc).isoformat()

    return {
        "station": station,
        "source": "Open-Meteo",
        "timezone": payload.get("timezone"),
        "current_time": current_time,
        "current_time_utc": current_time_utc,
        "update_interval_seconds": current.get("interval"),
        "weather_code": current.get("weather_code"),
        "weather_description": WEATHER_CODE_DESCRIPTIONS.get(
            current.get("weather_code")
        ),
        "current_temperature_c": current.get("temperature_2m"),
        "apparent_temperature_c": current.get("apparent_temperature"),
        "dew_point_c": current.get("dew_point_2m"),
        "today_min_temperature_c": first_daily_value("temperature_2m_min"),
        "today_max_temperature_c": first_daily_value("temperature_2m_max"),
        "precipitation_last_hour_mm": current.get("precipitation"),
        "rain_mm": current.get("rain"),
        "showers_mm": current.get("showers"),
        "snowfall_cm": current.get("snowfall"),
        "relative_humidity_pct": current.get("relative_humidity_2m"),
        "cloud_cover_pct": current.get("cloud_cover"),
        "pressure_msl_hpa": current.get("pressure_msl"),
        "surface_pressure_hpa": current.get("surface_pressure"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "wind_direction_degrees": current.get("wind_direction_10m"),
        "wind_gusts_kmh": current.get("wind_gusts_10m"),
        "visibility_m": current.get("visibility"),
        "sunrise": first_daily_value("sunrise"),
        "sunset": first_daily_value("sunset"),
    }


def fetch_daily_forecast(station: str, target_date: date) -> dict[str, Any] | None:
    normalized_station = station.strip().casefold()
    coordinates = CITY_COORDINATES.get(normalized_station)
    if coordinates is None:
        raise ValueError(f"No current-weather coordinates for {station!r}.")

    response = requests.get(
        OPEN_METEO_API_URL,
        params={
            "latitude": coordinates[0],
            "longitude": coordinates[1],
            "daily": (
                "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                "weather_code"
            ),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "timezone": "auto",
            "forecast_days": 8,
        },
        timeout=15,
    )
    response.raise_for_status()

    payload = response.json()
    daily = payload.get("daily") if isinstance(payload, dict) else None
    if not isinstance(daily, dict) or not isinstance(daily.get("time"), list):
        raise ValueError("Open-Meteo returned an invalid daily-forecast response.")

    try:
        index = daily["time"].index(target_date.isoformat())
    except ValueError:
        return None

    def value(name: str) -> Any:
        values = daily.get(name)
        return values[index] if isinstance(values, list) and index < len(values) else None

    weather_code = value("weather_code")
    return {
        "date": target_date.isoformat(),
        "source": "Open-Meteo",
        "forecast_type": "provider_forecast",
        "temperature_min_c": value("temperature_2m_min"),
        "temperature_max_c": value("temperature_2m_max"),
        "precipitation_sum_mm": value("precipitation_sum"),
        "weather_code": weather_code,
        "weather_description": WEATHER_CODE_DESCRIPTIONS.get(weather_code),
    }
