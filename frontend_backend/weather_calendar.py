from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

MAX_FORECAST_DAYS = 7


def calendar_date_mode(
    selected_date: date,
    timezone_name: str,
    now: datetime | None = None,
) -> tuple[str, date, date]:
    """Classify a calendar date against the selected location's local day."""
    timezone = ZoneInfo(timezone_name)
    if now is None:
        local_now = datetime.now(timezone)
    elif now.tzinfo is None:
        local_now = now.replace(tzinfo=timezone)
    else:
        local_now = now.astimezone(timezone)
    local_today = local_now.date()
    max_forecast_date = local_today + timedelta(days=MAX_FORECAST_DAYS)

    if selected_date < local_today:
        return "historical", local_today, max_forecast_date
    if selected_date == local_today:
        return "current", local_today, max_forecast_date
    if selected_date <= max_forecast_date:
        return "forecast", local_today, max_forecast_date
    raise ValueError(
        f"Date is outside the {MAX_FORECAST_DAYS}-day forecast window."
    )
