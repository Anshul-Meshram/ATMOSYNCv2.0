from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import Response

from app.config.locations import get_station_by_city, WEATHER_STATIONS
from app.db.session import AsyncSessionLocal
from app.models.weather import WeatherObservation, WeatherStationResponse
from app.repositories.weather import WeatherRepository
from app.services.report import generate_weekly_report


router = APIRouter(
    prefix="/weather",
    tags=["weather"],
)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.get(
    "/stations",
    response_model=list[WeatherStationResponse],
)
async def get_stations() -> list[WeatherStationResponse]:
    return[
        WeatherStationResponse(
            city=station.city,
            climate_identifier=station.climate_identifier,
            available_from=station.available_from,
        )
        for station in WEATHER_STATIONS
    ]


@router.get("/report/weekly")
async def get_weekly_report(
    start_date: date = Query(...),
    session: AsyncSession = Depends(get_session),
):
    end_date = start_date + timedelta(days=6)

    repository = WeatherRepository(session)

    observations = await repository.get_weekly_observations(
        start_date=start_date,
        end_date=end_date,
    )

    pdf_bytes = generate_weekly_report(
        observations=observations,
        start_date=start_date,
        end_date=end_date,
        stations=WEATHER_STATIONS,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="weather_report_{start_date}.pdf"'
            )
        },
    )


@router.get(
    "/{city}",
    response_model=list[WeatherObservation],
)
async def get_weather(
    city: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
    session: AsyncSession = Depends(get_session),
) -> list[WeatherObservation]:

    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be later than end_date.",
        )

    station = get_station_by_city(city)

    if station is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown weather station city: {city}",
        )

    repository = WeatherRepository(session)

    return await repository.get_observations(
        climate_identifier=station.climate_identifier,
        start_date=start_date,
        end_date=end_date,
    )
