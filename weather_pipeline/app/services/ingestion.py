import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.eccc import ECCCClient
from app.repositories.weather import WeatherRepository
from app.services.normalizer import normalize_observations


logger = logging.getLogger(__name__)

class WeatherIngestionService:
    """
    Coordinates the weather ingestion pipeline.

    Responsibilities:
    1. Fetch observations from ECCC.
    2. Normalize them into the Atmosync domain model.
    3. Persist them in PostgreSQL.
    """

    def __init__(
        self,
        eccc_client: ECCCClient,
        repository: WeatherRepository,
    ) -> None:
        self.eccc_client = eccc_client
        self.repository = repository

    async def ingest_daily(
        self,
        climate_identifier: str,
        start_date: date,
        end_date: date,
    ) -> int:
        """
        Fetch and persist daily weather observations.

        Returns the number of observations received from ECCC.
        """

        logger.info(
            "Ingestion started: climate_id=%s start_date=%s end_date=%s",
            climate_identifier,
            start_date,
            end_date,
        )

        try:
            eccc_observations = await self.eccc_client.fetch_daily(
                climate_identifier=climate_identifier,
                start_date=start_date,
                end_date=end_date,
            )

            if not eccc_observations:
                logger.warning(
                    "No observations available from ECCC: "
                    "climate_id=%s start_date=%s end_date=%s",
                    climate_identifier,
                    start_date,
                    end_date,
                )
                return 0

            weather_observations = normalize_observations(
                eccc_observations
            )

            await self.repository.upsert_observations(
                weather_observations
            )

            count = len(weather_observations)

            logger.info(
                "Ingestion completed: climate_id=%s observations=%d",
                climate_identifier,
                count,
            )

            return count

        except Exception:
            logger.exception(
                "Ingestion failed: climate_id=%s "
                "start_date=%s end_date=%s",
                climate_identifier,
                start_date,
                end_date,
            )
            raise


def create_ingestion_service(
    eccc_client: ECCCClient,
    session: AsyncSession,
) -> WeatherIngestionService:
    """
    Construct the ingestion service with its repository.
    """

    repository = WeatherRepository(session)

    return WeatherIngestionService(
        eccc_client=eccc_client,
        repository=repository,
    )
