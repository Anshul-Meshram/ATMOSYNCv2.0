import logging
from collections.abc import Awaitable, Callable
from datetime import date, timedelta

logger = logging.getLogger(__name__)


async def run_daily_ingestion(
    ingestion_runner: Callable[[date, date], Awaitable[None]],
) -> None:
    """
    Run ingestion for the previous available calendar day.

    The actual ingestion implementation is supplied by the application.
    """

    target_date = date.today() - timedelta(days=1)

    logger.info(
        "Scheduled daily ingestion started: date=%s",
        target_date,
    )

    try:
        await ingestion_runner(
            start_date=target_date,
            end_date=target_date,
        )

        logger.info(
            "Scheduled daily ingestion completed: date=%s",
            target_date,
        )

    except Exception:
        logger.exception(
            "Scheduled daily ingestion failed: date=%s",
            target_date,
        )
