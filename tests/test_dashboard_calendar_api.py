import unittest
from datetime import date
from unittest.mock import patch

from frontend_backend import server


class CalendarApiTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    @patch("frontend_backend.server.get_anomaly_rows", return_value=[])
    @patch(
        "frontend_backend.server.get_forecast_rows",
        return_value=[
            {
                "forecast_date": "2026-03-09",
                "generated_at": "2026-03-08T12:00:00+00:00",
            },
            {
                "forecast_date": "2026-03-10",
                "generated_at": "2026-03-08T13:00:00+00:00",
            },
        ],
    )
    def test_forecast_api_exposes_latest_generation_timestamp(
        self,
        _forecast_rows,
        _anomaly_rows,
    ):
        response = self.client.get("/api/weather/forecast?station=toronto")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["generated_at"],
            "2026-03-08T13:00:00+00:00",
        )

    def test_rejects_invalid_date_format(self):
        response = self.client.get(
            "/api/weather/calendar?station=toronto&date=2026-3-7"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("YYYY-MM-DD", response.get_json()["error"])

    @patch("frontend_backend.server.fetch_eccc_observations", return_value=[])
    @patch(
        "frontend_backend.server.calendar_date_mode",
        return_value=("historical", date(2026, 3, 8), date(2026, 3, 15)),
    )
    def test_empty_historical_day_is_returned_without_forecast_substitution(
        self,
        _calendar_mode,
        _fetch_observations,
    ):
        response = self.client.get(
            "/api/weather/calendar?station=toronto&date=2026-03-07"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["mode"], "historical")
        self.assertEqual(payload["eccc_observations"], [])
        self.assertIsNone(payload["provider_forecast"])
        self.assertIsNone(payload["ml_forecast"])

    @patch(
        "frontend_backend.server._get_station_forecast_for_date",
        return_value=(
            {
                "forecast_date": "2026-03-15",
                "generated_at": "2026-03-08T12:00:00+00:00",
                "min_temp_c": -2.0,
            },
            [],
        ),
    )
    @patch(
        "frontend_backend.server.fetch_daily_forecast",
        return_value={
            "date": "2026-03-15",
            "source": "Open-Meteo",
            "forecast_type": "provider_forecast",
        },
    )
    @patch(
        "frontend_backend.server.calendar_date_mode",
        return_value=("forecast", date(2026, 3, 8), date(2026, 3, 15)),
    )
    def test_seventh_future_day_keeps_provider_and_ml_forecasts_separate(
        self,
        _calendar_mode,
        _provider_forecast,
        _ml_forecast,
    ):
        response = self.client.get(
            "/api/weather/calendar?station=toronto&date=2026-03-15"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["mode"], "forecast")
        self.assertEqual(payload["provider_forecast"]["source"], "Open-Meteo")
        self.assertEqual(payload["ml_forecast"]["forecast_date"], "2026-03-15")
        self.assertEqual(payload["anomalies"], [])


if __name__ == "__main__":
    unittest.main()
