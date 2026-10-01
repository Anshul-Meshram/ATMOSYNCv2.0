from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ECCCObservation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    climate_identifier: str = Field(min_length=1)
    observation_date: date

    mean_temperature: Decimal | None = None
    mean_temperature_flag: str | None = None

    min_temperature: Decimal | None = None
    min_temperature_flag: str | None = None

    max_temperature: Decimal | None = None
    max_temperature_flag: str | None = None

    total_precipitation: Decimal | None = None
    total_precipitation_flag: str | None = None

    total_rain: Decimal | None = None
    total_rain_flag: str | None = None

    total_snow: Decimal | None = None
    total_snow_flag: str | None = None

    snow_on_ground: Decimal | None = None
    snow_on_ground_flag: str | None = None

    direction_max_gust: Decimal | None = None
    direction_max_gust_flag: str | None = None

    speed_max_gust: Decimal | None = None
    speed_max_gust_flag: str | None = None

    cooling_degree_days: Decimal | None = None
    cooling_degree_days_flag: str | None = None

    heating_degree_days: Decimal | None = None
    heating_degree_days_flag: str | None = None

    min_relative_humidity: Decimal | None = None
    min_relative_humidity_flag: str | None = None
