import unittest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from frontend_backend.calendar_weather import fetch_eccc_observations
from frontend_backend.current_weather import fetch_daily_forecast
from frontend_backend.weather_calendar import calendar_date_mode


class WeatherCalendarTests(unittest.TestCase):
    def test_calendar_uses_location_date_and_includes_seventh_forecast_day(self):
        timezone = ZoneInfo("America/Toronto")
        local_now = datetime(2026, 3, 8, 0, 30, tzinfo=timezone)

        mode, local_today, max_forecast_date = calendar_date_mode(
            date(2026, 3, 15),
            "America/Toronto",
            now=local_now,
        )

        self.assertEqual(mode, "forecast")
        self.assertEqual(local_today, date(2026, 3, 8))
        self.assertEqual(max_forecast_date, date(2026, 3, 15))

        with self.assertRaises(ValueError):
            calendar_date_mode(
                date(2026, 3, 16),
                "America/Toronto",
                now=local_now,
            )

    @patch("frontend_backend.calendar_weather.requests.get")
    def test_historical_fetch_masks_forecast_filled_fields(self, get):
        target = date(2026, 3, 7)
        response = Mock()
        response.json.return_value = [
            {
                "observation_date": target.isoformat(),
                "mean_temperature": 2.5,
                "min_temperature": 1.0,
                "max_temperature": 8.0,
                "total_precipitation": 4.0,
                "total_rain": 0.0,
                "field_sources": {
                    "mean_temperature": "actual",
                    "min_temperature": "actual",
                    "max_temperature": "forecast",
                    "total_precipitation": "forecast",
                },
            },
            {
                "observation_date": "2026-03-08",
                "mean_temperature": 9.0,
            },
        ]
        get.return_value = response

        result = fetch_eccc_observations(
            "https://weather.example/api/",
            "Quebec City",
            target,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["mean_temperature"], 2.5)
        self.assertEqual(result[0]["min_temperature"], 1.0)
        self.assertIsNone(result[0]["max_temperature"])
        self.assertIsNone(result[0]["total_precipitation"])
        self.assertEqual(result[0]["total_rain"], 0.0)
        self.assertEqual(result[0]["source"], "ECCC")
        self.assertEqual(
            get.call_args.args[0],
            "https://weather.example/api/weather/Quebec%20City",
        )
        self.assertEqual(
            get.call_args.kwargs["params"]["start_date"],
            target.isoformat(),
        )

    @patch("frontend_backend.current_weather.requests.get")
    def test_provider_forecast_includes_seventh_day(self, get):
        start = date(2026, 3, 8)
        dates = [(start + timedelta(days=offset)).isoformat() for offset in range(8)]
        response = Mock()
        response.json.return_value = {
            "timezone": "America/Toronto",
            "daily": {
                "time": dates,
                "temperature_2m_min": list(range(-2, 6)),
                "temperature_2m_max": list(range(3, 11)),
                "precipitation_sum": [0.0] * 8,
                "weather_code": [1] * 8,
            },
        }
        get.return_value = response

        result = fetch_daily_forecast("Toronto", start + timedelta(days=7))

        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "2026-03-15")
        self.assertEqual(result["temperature_min_c"], 5)
        self.assertEqual(result["temperature_max_c"], 10)
        self.assertEqual(result["forecast_type"], "provider_forecast")
        self.assertEqual(get.call_args.kwargs["params"]["forecast_days"], 8)


if __name__ == "__main__":
    unittest.main()
