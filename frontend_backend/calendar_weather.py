from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import quote, urljoin

import requests

FORECASTABLE_OBSERVATION_FIELDS = (
    "mean_temperature",
    "min_temperature",
    "max_temperature",
    "total_precipitation",
)

OBSERVATION_FIELDS = (
    "mean_temperature",
    "min_temperature",
    "max_temperature",
    "total_precipitation",
    "total_rain",
    "total_snow",
    "snow_on_ground",
    "speed_max_gust",
    "min_relative_humidity",
)


def fetch_eccc_observations(
    base_url: str,
    station: str,
    target_date: date,
) -> list[dict[str, Any]]:
    """Fetch one day's weather and discard any forecast-filled values."""
    endpoint = urljoin(
        f"{base_url.rstrip('/')}/",
        f"weather/{quote(station, safe='')}",
    )
    response = requests.get(
        endpoint,
        params={
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        },
        timeout=8,
    )
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict):
        records = next(
            (
                payload[key]
                for key in ("data", "results", "records", "weather", "observations")
                if isinstance(payload.get(key), list)
            ),
            None,
        )
    else:
        records = payload

    if not isinstance(records, list):
        raise ValueError("Weather API response does not contain observation records.")

    observations: list[dict[str, Any]] = []
    for source_record in records:
        if not isinstance(source_record, dict):
            continue
        record_date = source_record.get(
            "observation_date",
            source_record.get("date", source_record.get("Date/Time")),
        )
        if not isinstance(record_date, str) or record_date[:10] != target_date.isoformat():
            continue

        record = dict(source_record)
        field_sources = record.get("field_sources")
        if isinstance(field_sources, dict):
            for field in FORECASTABLE_OBSERVATION_FIELDS:
                if field_sources.get(field) != "actual":
                    record[field] = None

        if not any(record.get(field) is not None for field in OBSERVATION_FIELDS):
            continue

        record["source"] = "ECCC"
        record["data_type"] = "observed"
        observations.append(record)

    return observations
