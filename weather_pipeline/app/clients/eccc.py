from datetime import date
from typing import Any

import httpx

from app.models.eccc import ECCCObservation
from app.config.settings import settings



class ECCCClient:
    """
    Client for retrieving daily climate observations from ECCC.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
    ) -> None:
        self.http_client = http_client

    async def fetch_daily(
        self,
        climate_identifier: str,
        start_date: date,
        end_date: date,
    ) -> list[ECCCObservation]:
        """
        Fetch all daily observations for a climate station
        within the requested date range.

        Pagination is controlled exclusively by ECCC's `rel=next`
        link. We intentionally do not use `numberMatched`.
        """

        url = build_daily_url(
            climate_identifier=climate_identifier,
            start_date=start_date,
            end_date=end_date,
        )

        observations: list[ECCCObservation] = []

        while url:
            response = await self.http_client.get(url)
            response.raise_for_status()

            data = response.json()

            for feature in data.get("features", []):
                observation = parse_observation(feature)
                observations.append(observation)

            url = get_next_url(data)

        return observations


def build_daily_url(
    climate_identifier: str,
    start_date: date,
    end_date: date,
    limit: int = 100,
) -> str:
    params = {
        "CLIMATE_IDENTIFIER": climate_identifier,
        "datetime": (
            f"{start_date.isoformat()}"
            f"/{end_date.isoformat()}"
        ),
        "limit": limit,
    }

    request = httpx.Request(
        "GET",
        settings.eccc_base_url,
        params=params,
    )

    return str(request.url)


def get_next_url(data: dict[str, Any]) -> str | None:
    """
    Extract ECCC's pagination URL from the response.

    ECCC provides pagination through a link such as:

        {
            "rel": "next",
            "href": "..."
        }

    If there is no next link, pagination is complete.
    """

    for link in data.get("links", []):
        if link.get("rel") == "next":
            return link.get("href")

    return None


def parse_observation(
    feature: dict[str, Any],
) -> ECCCObservation:
    properties = feature["properties"]
    

    return ECCCObservation(
        climate_identifier=properties["CLIMATE_IDENTIFIER"],
        observation_date=properties["LOCAL_DATE"],

        mean_temperature=properties.get("MEAN_TEMPERATURE"),
        mean_temperature_flag=properties.get("MEAN_TEMPERATURE_FLAG"),

        min_temperature=properties.get("MIN_TEMPERATURE"),
        min_temperature_flag=properties.get("MIN_TEMPERATURE_FLAG"),

        max_temperature=properties.get("MAX_TEMPERATURE"),
        max_temperature_flag=properties.get("MAX_TEMPERATURE_FLAG"),

        total_precipitation=properties.get("TOTAL_PRECIPITATION"),
        total_precipitation_flag=properties.get(
            "TOTAL_PRECIPITATION_FLAG"
        ),

        total_rain=properties.get("TOTAL_RAIN"),
        total_rain_flag=properties.get("TOTAL_RAIN_FLAG"),

        total_snow=properties.get("TOTAL_SNOW"),
        total_snow_flag=properties.get("TOTAL_SNOW_FLAG"),

        snow_on_ground=properties.get("SNOW_ON_GROUND"),
        snow_on_ground_flag=properties.get(
            "SNOW_ON_GROUND_FLAG"
        ),

        direction_max_gust=properties.get("DIRECTION_MAX_GUST"),
        direction_max_gust_flag=properties.get(
            "DIRECTION_MAX_GUST_FLAG"
        ),

        speed_max_gust=properties.get("SPEED_MAX_GUST"),
        speed_max_gust_flag=properties.get(
            "SPEED_MAX_GUST_FLAG"
        ),

        cooling_degree_days=properties.get("COOLING_DEGREE_DAYS"),
        cooling_degree_days_flag=properties.get(
            "COOLING_DEGREE_DAYS_FLAG"
        ),

        heating_degree_days=properties.get("HEATING_DEGREE_DAYS"),
        heating_degree_days_flag=properties.get(
            "HEATING_DEGREE_DAYS_FLAG"
        ),

        min_relative_humidity=properties.get("MIN_REL_HUMIDITY"),
        min_relative_humidity_flag=properties.get(
            "MIN_REL_HUMIDITY_FLAG"
        ),
    )
