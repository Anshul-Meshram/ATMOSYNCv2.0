import unittest
from unittest.mock import Mock, patch

from frontend_backend.current_weather import fetch_current_weather


class CurrentWeatherTests(unittest.TestCase):
    @patch("frontend_backend.current_weather.requests.get")
    def test_maps_current_weather_and_daily_extremes(self, get):
        response = Mock()
        response.json.return_value = {
            "timezone": "America/Toronto",
            "utc_offset_seconds": -18000,
            "current": {
                "time": "2026-11-26T13:00",
                "interval": 900,
                "temperature_2m": 5.7,
                "relative_humidity_2m": 47,
                "dew_point_2m": 1.8,
                "apparent_temperature": 2.1,
                "precipitation": 0.0,
                "rain": 0.0,
                "showers": 0.0,
                "snowfall": 0.0,
                "weather_code": 3,
                "cloud_cover": 90,
                "pressure_msl": 1014.2,
                "surface_pressure": 1001.1,
                "wind_speed_10m": 28.4,
                "wind_direction_10m": 68,
                "wind_gusts_10m": 42.0,
                "visibility": 24000,
            },
            "daily": {
                "time": ["2026-11-26"],
                "temperature_2m_max": [6.0],
                "temperature_2m_min": [1.3],
                "precipitation_sum": [13.6],
                "sunrise": ["2026-11-26T07:25"],
                "sunset": ["2026-11-26T16:44"],
            },
        }
        get.return_value = response

        result = fetch_current_weather("Toronto")

        self.assertEqual(result["station"], "Toronto")
        self.assertEqual(result["current_time"], "2026-11-26T13:00")
        self.assertEqual(result["current_time_utc"], "2026-11-26T18:00:00+00:00")
        self.assertEqual(result["update_interval_seconds"], 900)
        self.assertEqual(result["weather_description"], "Overcast")
        self.assertEqual(result["current_temperature_c"], 5.7)
        self.assertEqual(result["apparent_temperature_c"], 2.1)
        self.assertEqual(result["dew_point_c"], 1.8)
        self.assertEqual(result["today_min_temperature_c"], 1.3)
        self.assertEqual(result["today_max_temperature_c"], 6.0)
        self.assertEqual(result["precipitation_last_hour_mm"], 0.0)
        self.assertEqual(result["relative_humidity_pct"], 47)
        self.assertEqual(result["wind_speed_kmh"], 28.4)
        self.assertEqual(result["wind_direction_degrees"], 68)
        self.assertEqual(result["wind_gusts_kmh"], 42.0)
        self.assertEqual(result["visibility_m"], 24000)
        self.assertEqual(result["pressure_msl_hpa"], 1014.2)
        self.assertEqual(result["sunrise"], "2026-11-26T07:25")
        self.assertEqual(result["sunset"], "2026-11-26T16:44")
        self.assertEqual(
            get.call_args.kwargs["params"]["timezone"],
            "auto",
        )
        self.assertEqual(
            get.call_args.kwargs["params"]["wind_speed_unit"],
            "kmh",
        )

    @patch("frontend_backend.current_weather.requests.get")
    def test_rejects_unknown_station(self, get):
        with self.assertRaises(ValueError):
            fetch_current_weather("Unknown City")
        get.assert_not_called()

    @patch("frontend_backend.current_weather.requests.get")
    def test_rejects_malformed_api_response(self, get):
        response = Mock()
        response.json.return_value = {"current": [], "daily": []}
        get.return_value = response

        with self.assertRaises(ValueError):
            fetch_current_weather("Toronto")


if __name__ == "__main__":
    unittest.main()
