from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WeatherStation:
    city: str
    climate_identifier: str
    available_from: date


WEATHER_STATIONS = [
    WeatherStation(
        city="Toronto",
        climate_identifier="6158355",
        available_from=date(2002, 1, 1),
    ),
    WeatherStation(
        city="Montreal",
        climate_identifier="7014160",
        available_from=date(1930, 1, 1),
    ),
    WeatherStation(
        city="Vancouver",
        climate_identifier="1108446",
        available_from=date(1925, 1, 1),
    ),
    WeatherStation(
        city="Calgary",
        climate_identifier="3031094",
        available_from=date(1999, 1, 1),
    ),
    WeatherStation(
        city="Edmonton",
        climate_identifier="3012209",
        available_from=date(1996, 1, 1),
    ),
    WeatherStation(
        city="Ottawa",
        climate_identifier="6105978",
        available_from=date(2000, 1, 1),
    ),
    WeatherStation(
        city="Winnipeg",
        climate_identifier="502S001",
        available_from=date(1996, 1, 1),
    ),
    WeatherStation(
        city="Quebec City",
        climate_identifier="701S001",
        available_from=date(1992, 1, 1),
    ),
    WeatherStation(
        city="Halifax",
        climate_identifier="8202251",
        available_from=date(2012, 1, 1),
    ),
]

def get_station_by_city(city: str) -> WeatherStation | None:
    normalized_city = city.strip().casefold()

    for station in WEATHER_STATIONS:
        if station.city.casefold() == normalized_city:
            return station

    return None
