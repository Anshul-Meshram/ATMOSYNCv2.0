from datetime import date
from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weather import WeatherObservation


GET_WEEKLY_WEATHER_OBSERVATIONS = text(\
    """
    SELECT
        climate_identifier,
        observation_date,
        mean_temperature,
        min_temperature,
        max_temperature,
        total_precipitation,
        total_rain,
        total_snow,
        snow_on_ground
    FROM weather_observations
    WHERE observation_date BETWEEN :start_date AND :end_date
    ORDER BY climate_identifier, observation_date
    """
)

GET_WEATHER_OBSERVATIONS = text(
    """
    SELECT
        climate_identifier,
        observation_date,

        mean_temperature,
        mean_temperature_flag,

        min_temperature,
        min_temperature_flag,

        max_temperature,
        max_temperature_flag,

        total_precipitation,
        total_precipitation_flag,

        total_rain,
        total_rain_flag,

        total_snow,
        total_snow_flag,

        snow_on_ground,
        snow_on_ground_flag,

        direction_max_gust,
        direction_max_gust_flag,

        speed_max_gust,
        speed_max_gust_flag,

        cooling_degree_days,
        cooling_degree_days_flag,

        heating_degree_days,
        heating_degree_days_flag,

        min_relative_humidity,
        min_relative_humidity_flag

    FROM weather_observations

    WHERE climate_identifier = :climate_identifier
    AND observation_date BETWEEN :start_date AND :end_date

    ORDER BY observation_date ASC
    """
)

UPSERT_WEATHER_OBSERVATION = text(
    """
    INSERT INTO weather_observations (
        climate_identifier,
        observation_date,

        mean_temperature,
        mean_temperature_flag,

        min_temperature,
        min_temperature_flag,

        max_temperature,
        max_temperature_flag,

        total_precipitation,
        total_precipitation_flag,

        total_rain,
        total_rain_flag,

        total_snow,
        total_snow_flag,

        snow_on_ground,
        snow_on_ground_flag,

        direction_max_gust,
        direction_max_gust_flag,

        speed_max_gust,
        speed_max_gust_flag,

        cooling_degree_days,
        cooling_degree_days_flag,

        heating_degree_days,
        heating_degree_days_flag,

        min_relative_humidity,
        min_relative_humidity_flag
    )
    VALUES (
        :climate_identifier,
        :observation_date,

        :mean_temperature,
        :mean_temperature_flag,

        :min_temperature,
        :min_temperature_flag,

        :max_temperature,
        :max_temperature_flag,

        :total_precipitation,
        :total_precipitation_flag,

        :total_rain,
        :total_rain_flag,

        :total_snow,
        :total_snow_flag,

        :snow_on_ground,
        :snow_on_ground_flag,

        :direction_max_gust,
        :direction_max_gust_flag,

        :speed_max_gust,
        :speed_max_gust_flag,

        :cooling_degree_days,
        :cooling_degree_days_flag,

        :heating_degree_days,
        :heating_degree_days_flag,

        :min_relative_humidity,
        :min_relative_humidity_flag
    )
    ON CONFLICT (
        climate_identifier,
        observation_date
    )
    DO UPDATE SET
        mean_temperature = EXCLUDED.mean_temperature,
        mean_temperature_flag = EXCLUDED.mean_temperature_flag,

        min_temperature = EXCLUDED.min_temperature,
        min_temperature_flag = EXCLUDED.min_temperature_flag,

        max_temperature = EXCLUDED.max_temperature,
        max_temperature_flag = EXCLUDED.max_temperature_flag,

        total_precipitation = EXCLUDED.total_precipitation,
        total_precipitation_flag = EXCLUDED.total_precipitation_flag,

        total_rain = EXCLUDED.total_rain,
        total_rain_flag = EXCLUDED.total_rain_flag,

        total_snow = EXCLUDED.total_snow,
        total_snow_flag = EXCLUDED.total_snow_flag,

        snow_on_ground = EXCLUDED.snow_on_ground,
        snow_on_ground_flag = EXCLUDED.snow_on_ground_flag,

        direction_max_gust = EXCLUDED.direction_max_gust,
        direction_max_gust_flag = EXCLUDED.direction_max_gust_flag,

        speed_max_gust = EXCLUDED.speed_max_gust,
        speed_max_gust_flag = EXCLUDED.speed_max_gust_flag,

        cooling_degree_days = EXCLUDED.cooling_degree_days,
        cooling_degree_days_flag = EXCLUDED.cooling_degree_days_flag,

        heating_degree_days = EXCLUDED.heating_degree_days,
        heating_degree_days_flag = EXCLUDED.heating_degree_days_flag,

        min_relative_humidity = EXCLUDED.min_relative_humidity,
        min_relative_humidity_flag = EXCLUDED.min_relative_humidity_flag,

        updated_at = CURRENT_TIMESTAMP
    """
)


class WeatherRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_observations(
        self,
        observations: Sequence[WeatherObservation],
    ) -> None:
        if not observations:
            return

        values = [
            {
                "climate_identifier": observation.climate_identifier,
                "observation_date": observation.observation_date,

                "mean_temperature": observation.mean_temperature,
                "mean_temperature_flag": observation.mean_temperature_flag,

                "min_temperature": observation.min_temperature,
                "min_temperature_flag": observation.min_temperature_flag,

                "max_temperature": observation.max_temperature,
                "max_temperature_flag": observation.max_temperature_flag,

                "total_precipitation": observation.total_precipitation,
                "total_precipitation_flag": (
                    observation.total_precipitation_flag
                ),

                "total_rain": observation.total_rain,
                "total_rain_flag": observation.total_rain_flag,

                "total_snow": observation.total_snow,
                "total_snow_flag": observation.total_snow_flag,

                "snow_on_ground": observation.snow_on_ground,
                "snow_on_ground_flag": (
                    observation.snow_on_ground_flag
                ),

                "direction_max_gust": observation.direction_max_gust,
                "direction_max_gust_flag": (
                    observation.direction_max_gust_flag
                ),

                "speed_max_gust": observation.speed_max_gust,
                "speed_max_gust_flag": (
                    observation.speed_max_gust_flag
                ),

                "cooling_degree_days": (
                    observation.cooling_degree_days
                ),
                "cooling_degree_days_flag": (
                    observation.cooling_degree_days_flag
                ),

                "heating_degree_days": (
                    observation.heating_degree_days
                ),
                "heating_degree_days_flag": (
                    observation.heating_degree_days_flag
                ),

                "min_relative_humidity": (
                    observation.min_relative_humidity
                ),
                "min_relative_humidity_flag": (
                    observation.min_relative_humidity_flag
                ),
            }
            for observation in observations
        ]

        await self.session.execute(
            UPSERT_WEATHER_OBSERVATION,
            values,
        )
        await self.session.commit()

    async def get_observations(
        self,
        climate_identifier: str,
        start_date: date,
        end_date: date,
    ) -> list[WeatherObservation]:
        result = await self.session.execute(
            GET_WEATHER_OBSERVATIONS,
            {
                "climate_identifier": climate_identifier,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        rows = result.mappings().all()

        return [
            WeatherObservation(**row)
            for row in rows
        ]
        
    async def get_weekly_observations(
        self,
        start_date: date,
        end_date: date,
    ) -> list[WeatherObservation]:
        result = await self.session.execute(
            GET_WEEKLY_WEATHER_OBSERVATIONS,
            {
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        
        rows = result.mappings().all()

        return [ 
            WeatherObservation(**row)
            for row in rows
        ]
