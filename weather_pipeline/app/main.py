import argparse
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import date

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.clients.eccc import ECCCClient
from app.config.locations import WEATHER_STATIONS
from app.config.settings import settings
from app.db.session import AsyncSessionLocal, close_database
from app.scheduler.jobs import run_daily_ingestion
from app.services.ingestion import create_ingestion_service
from app.api.weather import router as weather_router


PROJECT_HISTORY_START = date(2020, 1, 1)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


scheduler = AsyncIOScheduler(
    timezone=settings.scheduler_timezone,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest daily weather observations from ECCC."
    )

    parser.add_argument(
        "--start-date",
        required=True,
        type=date.fromisoformat,
        help="Start date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--end-date",
        required=True,
        type=date.fromisoformat,
        help="End date in YYYY-MM-DD format.",
    )

    return parser.parse_args()


async def run_ingestion(
    start_date: date,
    end_date: date,
) -> None:
    if start_date > end_date:
        raise ValueError(
            "start-date cannot be later than end-date."
        )

    requested_start = max(
        start_date,
        PROJECT_HISTORY_START,
    )

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        eccc_client = ECCCClient(http_client=http_client)

        async with AsyncSessionLocal() as session:
            ingestion_service = create_ingestion_service(
                eccc_client=eccc_client,
                session=session,
            )

            total_observations = 0

            for station in WEATHER_STATIONS:
                station_start = max(
                    requested_start,
                    station.available_from,
                )

                if station_start > end_date:
                    logger.info(
                        "Skipping station: city=%s climate_id=%s "
                        "no available data in requested range",
                        station.city,
                        station.climate_identifier,
                    )
                    continue

                logger.info(
                    "Starting ingestion: city=%s climate_id=%s "
                    "start_date=%s end_date=%s",
                    station.city,
                    station.climate_identifier,
                    station_start,
                    end_date,
                )

                count = await ingestion_service.ingest_daily(
                    climate_identifier=station.climate_identifier,
                    start_date=station_start,
                    end_date=end_date,
                )

                total_observations += count

                logger.info(
                    "Station ingestion completed: city=%s "
                    "climate_id=%s observations=%d",
                    station.city,
                    station.climate_identifier,
                    count,
                )

            logger.info(
                "Weather ingestion completed for all stations: "
                "stations=%d total_observations=%d "
                "start_date=%s end_date=%s",
                len(WEATHER_STATIONS),
                total_observations,
                requested_start,
                end_date,
            )


async def scheduled_ingestion() -> None:
    await run_daily_ingestion(
        ingestion_runner=run_ingestion,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Atmosync weather pipeline")

    if settings.enable_scheduler:    
        scheduler.add_job(
            scheduled_ingestion,
            trigger="cron",
            hour=settings.daily_ingestion_hour,
            minute=settings.daily_ingestion_minute,
            id="daily_weather_ingestion",
            replace_existing=True,
        )

        scheduler.start()

        logger.info(
            "Daily weather ingestion scheduled: %02d:%02d %s",
            settings.daily_ingestion_hour,
            settings.daily_ingestion_minute,
            settings.scheduler_timezone,
        )   
    else:
        logger.info("In-process scheduler disabled")

    try:
        yield
    finally:
        if settings.enable_scheduler:
            logger.info("Shutting down scheduler")
            scheduler.shutdown(wait=False)

        await close_database()

        logger.info("Atmosync weather pipeline stopped")


app = FastAPI(
    title="Atmosync Weather Pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(weather_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
    }


async def cli_main() -> None:
    args = parse_args()

    try:
        await run_ingestion(
            start_date=args.start_date,
            end_date=args.end_date,
        )
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(cli_main())
