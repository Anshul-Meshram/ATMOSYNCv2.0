"""
AtmoSync Anomaly Detection & Classification Module.

Provides explainable, statistical anomaly detection comparing observed
or forecast values against historical baselines using z-scores and
rule-based severity classification.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
import logging
from pathlib import Path
from typing import Any, Sequence

import numpy as np

logger = logging.getLogger(__name__)

# Default z-score thresholds
TEMP_ANOMALY_THRESHOLD = 2.0
TEMP_EXTREME_THRESHOLD = 3.0
PRECIP_ANOMALY_THRESHOLD = 2.0
PRECIP_EXTREME_THRESHOLD = 3.5


@dataclass
class AnomalyResult:
    station: str
    station_id: str
    variable: str
    date: str
    value: float
    expected_baseline: float
    expected_range: list[float]
    anomaly_score: float  # z-score
    threshold: float
    status: str  # "normal" | "anomaly"
    label: str  # "normal", "warm_anomaly", "extreme_heat", "cold_anomaly", "extreme_cold", "heavy_precipitation", "extreme_precipitation"
    is_forecast: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ClimateAnomalyDetector:
    """
    Statistical anomaly detector and classifier.
    Computes baselines from recent history or training metadata,
    calculates z-scores, and classifies events.
    """

    def __init__(self, metadata_path: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        meta_file = metadata_path or (root / "models" / "Light_GBM" / "inference_metadata.json")
        if meta_file.exists():
            self.metadata = json.loads(meta_file.read_text(encoding="utf-8"))
        else:
            self.metadata = {}

        # Monthly climatological temperature baselines (°C) per Canadian station
        # Derived from historical Environment Canada normals
        self.station_monthly_temp_normals: dict[str, dict[int, tuple[float, float]]] = {
            # station: {month: (mean_temp, std_temp)}
            "toronto": {
                1: (-5.5, 4.0), 2: (-4.5, 3.8), 3: (0.1, 3.5), 4: (7.1, 3.2),
                5: (13.1, 3.0), 6: (18.6, 2.8), 7: (21.5, 2.5), 8: (20.6, 2.4),
                9: (16.2, 2.8), 10: (9.5, 3.0), 11: (3.7, 3.2), 12: (-2.2, 3.8),
            },
            "vancouver": {
                1: (4.1, 2.5), 2: (4.9, 2.3), 3: (6.9, 2.0), 4: (9.4, 1.8),
                5: (12.8, 1.8), 6: (15.7, 1.7), 7: (18.0, 1.6), 8: (18.0, 1.6),
                9: (14.9, 1.8), 10: (10.3, 1.9), 11: (6.3, 2.2), 12: (3.6, 2.4),
            },
            "calgary": {
                1: (-7.1, 5.5), 2: (-5.4, 5.0), 3: (-1.4, 4.2), 4: (4.2, 3.5),
                5: (9.4, 3.0), 6: (13.4, 2.8), 7: (16.5, 2.5), 8: (15.8, 2.6),
                9: (11.0, 3.2), 10: (5.2, 3.8), 11: (-2.4, 4.8), 12: (-6.8, 5.2),
            },
            "edmonton": {
                1: (-10.4, 6.0), 2: (-8.0, 5.5), 3: (-2.5, 4.5), 4: (5.4, 3.5),
                5: (11.5, 3.0), 6: (15.3, 2.6), 7: (17.7, 2.4), 8: (16.6, 2.5),
                9: (11.3, 3.0), 10: (4.7, 3.8), 11: (-4.3, 5.0), 12: (-9.6, 5.8),
            },
            "winnipeg": {
                1: (-16.4, 6.5), 2: (-13.2, 6.0), 3: (-5.8, 4.8), 4: (4.4, 3.8),
                5: (11.6, 3.2), 6: (17.0, 2.8), 7: (19.7, 2.5), 8: (18.8, 2.6),
                9: (12.7, 3.2), 10: (5.0, 3.8), 11: (-4.9, 5.2), 12: (-13.2, 6.2),
            },
            "ottawa": {
                1: (-10.3, 4.8), 2: (-8.1, 4.5), 3: (-2.3, 3.8), 4: (6.3, 3.2),
                5: (13.3, 2.8), 6: (18.5, 2.6), 7: (21.0, 2.4), 8: (19.8, 2.5),
                9: (15.0, 2.8), 10: (8.0, 3.2), 11: (1.5, 3.5), 12: (-6.2, 4.5),
            },
            "montreal": {
                1: (-9.7, 4.5), 2: (-7.7, 4.2), 3: (-2.0, 3.6), 4: (6.7, 3.0),
                5: (13.6, 2.8), 6: (18.9, 2.5), 7: (21.6, 2.3), 8: (20.5, 2.4),
                9: (15.7, 2.7), 10: (8.9, 3.0), 11: (2.5, 3.4), 12: (-5.6, 4.2),
            },
            "quebec city": {
                1: (-12.4, 4.8), 2: (-10.2, 4.5), 3: (-4.4, 3.8), 4: (4.0, 3.2),
                5: (11.1, 2.8), 6: (16.4, 2.5), 7: (19.3, 2.3), 8: (18.1, 2.4),
                9: (13.1, 2.7), 10: (6.4, 3.0), 11: (-0.3, 3.5), 12: (-8.1, 4.5),
            },
            "halifax": {
                1: (-4.1, 3.8), 2: (-3.7, 3.6), 3: (-0.2, 3.0), 4: (4.8, 2.5),
                5: (10.0, 2.3), 6: (15.1, 2.2), 7: (18.8, 2.1), 8: (18.9, 2.0),
                9: (15.1, 2.2), 10: (9.6, 2.5), 11: (4.7, 2.8), 12: (-1.0, 3.5),
            },
        }

    def get_temp_baseline(self, station: str, target_date: date) -> tuple[float, float]:
        norm_station = station.strip().lower().replace("_", " ")
        month = target_date.month
        station_normals = self.station_monthly_temp_normals.get(norm_station)
        if station_normals and month in station_normals:
            return station_normals[month]
        # Fallback to general Canadian seasonal baseline
        return (5.0, 5.0)

    def detect_temperature_anomaly(
        self,
        station: str,
        station_id: str,
        target_date: date,
        mean_temp: float,
        is_forecast: bool = False,
    ) -> AnomalyResult:
        baseline_mean, baseline_std = self.get_temp_baseline(station, target_date)
        z_score = (mean_temp - baseline_mean) / (baseline_std if baseline_std > 0 else 1.0)

        expected_min = round(baseline_mean - 2.0 * baseline_std, 1)
        expected_max = round(baseline_mean + 2.0 * baseline_std, 1)

        label = "normal"
        status = "normal"

        if z_score >= TEMP_EXTREME_THRESHOLD:
            label = "extreme_heat"
            status = "anomaly"
        elif z_score >= TEMP_ANOMALY_THRESHOLD:
            label = "warm_anomaly"
            status = "anomaly"
        elif z_score <= -TEMP_EXTREME_THRESHOLD:
            label = "extreme_cold"
            status = "anomaly"
        elif z_score <= -TEMP_ANOMALY_THRESHOLD:
            label = "cold_anomaly"
            status = "anomaly"

        return AnomalyResult(
            station=station,
            station_id=station_id,
            variable="mean_temp_c",
            date=target_date.isoformat(),
            value=round(mean_temp, 2),
            expected_baseline=round(baseline_mean, 2),
            expected_range=[expected_min, expected_max],
            anomaly_score=round(z_score, 2),
            threshold=TEMP_ANOMALY_THRESHOLD,
            status=status,
            label=label,
            is_forecast=is_forecast,
        )

    def detect_precipitation_anomaly(
        self,
        station: str,
        station_id: str,
        target_date: date,
        precip_mm: float,
        is_forecast: bool = False,
    ) -> AnomalyResult:
        # Typical daily precipitation baseline: mean ~2.5mm, std ~5.0mm
        baseline_mean = 2.5
        baseline_std = 5.0
        z_score = max(0.0, (precip_mm - baseline_mean) / baseline_std)

        expected_range = [0.0, 12.5]  # ~95th percentile daily cutoff

        label = "normal"
        status = "normal"

        if z_score >= PRECIP_EXTREME_THRESHOLD or precip_mm >= 30.0:
            label = "extreme_precipitation"
            status = "anomaly"
        elif z_score >= PRECIP_ANOMALY_THRESHOLD and precip_mm >= 12.0:
            label = "heavy_precipitation"
            status = "anomaly"

        return AnomalyResult(
            station=station,
            station_id=station_id,
            variable="precip_mm",
            date=target_date.isoformat(),
            value=round(precip_mm, 2),
            expected_baseline=round(baseline_mean, 2),
            expected_range=expected_range,
            anomaly_score=round(z_score, 2),
            threshold=PRECIP_ANOMALY_THRESHOLD,
            status=status,
            label=label,
            is_forecast=is_forecast,
        )

    def scan_forecast_anomalies(
        self,
        forecast_rows: Sequence[dict[str, Any]],
    ) -> list[AnomalyResult]:
        """Scan a 7-day forecast series for temperature and precipitation anomalies."""
        results: list[AnomalyResult] = []
        for row in forecast_rows:
            station = row.get("station", "unknown")
            station_id = row.get("station_id", "")
            d_str = row.get("forecast_date")
            if not d_str:
                continue
            f_date = date.fromisoformat(str(d_str))

            # Temperature anomaly check
            mean_temp = row.get("predicted_mean_temp_c") or row.get("mean_temp_c")
            if mean_temp is not None:
                results.append(
                    self.detect_temperature_anomaly(
                        station=station,
                        station_id=station_id,
                        target_date=f_date,
                        mean_temp=float(mean_temp),
                        is_forecast=True,
                    )
                )

            # Precipitation anomaly check
            precip = row.get("predicted_precip_mm") or row.get("precip_mm")
            if precip is not None:
                results.append(
                    self.detect_precipitation_anomaly(
                        station=station,
                        station_id=station_id,
                        target_date=f_date,
                        precip_mm=float(precip),
                        is_forecast=True,
                    )
                )

        return results
