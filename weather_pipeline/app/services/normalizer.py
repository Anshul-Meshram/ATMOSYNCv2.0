from app.models.eccc import ECCCObservation
from app.models.weather import WeatherObservation


def normalize_observation(
    observation: ECCCObservation,
) -> WeatherObservation:
    return WeatherObservation(
        climate_identifier=observation.climate_identifier,
        observation_date=observation.observation_date,

        mean_temperature=observation.mean_temperature,
        mean_temperature_flag=observation.mean_temperature_flag,

        min_temperature=observation.min_temperature,
        min_temperature_flag=observation.min_temperature_flag,

        max_temperature=observation.max_temperature,
        max_temperature_flag=observation.max_temperature_flag,

        total_precipitation=observation.total_precipitation,
        total_precipitation_flag=observation.total_precipitation_flag,

        total_rain=observation.total_rain,
        total_rain_flag=observation.total_rain_flag,

        total_snow=observation.total_snow,
        total_snow_flag=observation.total_snow_flag,

        snow_on_ground=observation.snow_on_ground,
        snow_on_ground_flag=observation.snow_on_ground_flag,

        direction_max_gust=observation.direction_max_gust,
        direction_max_gust_flag=observation.direction_max_gust_flag,

        speed_max_gust=observation.speed_max_gust,
        speed_max_gust_flag=observation.speed_max_gust_flag,

        cooling_degree_days=observation.cooling_degree_days,
        cooling_degree_days_flag=observation.cooling_degree_days_flag,

        heating_degree_days=observation.heating_degree_days,
        heating_degree_days_flag=observation.heating_degree_days_flag,

        min_relative_humidity=observation.min_relative_humidity,
        min_relative_humidity_flag=observation.min_relative_humidity_flag,
    )


def normalize_observations(
    observations: list[ECCCObservation],
) -> list[WeatherObservation]:
    return [
        normalize_observation(observation)
        for observation in observations
    ]
