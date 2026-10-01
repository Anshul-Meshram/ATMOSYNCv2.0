from collections import defaultdict
from datetime import date
from io import BytesIO
from typing import Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Paragraph,
    PageBreak,
)

from app.config.locations import WeatherStation
from app.models.weather import WeatherObservation


def _format_value(value) -> str:
    if value is None:
        return "—"

    return f"{value:.1f}"


def generate_weekly_report(
    observations: Sequence[WeatherObservation],
    start_date: date,
    end_date: date,
    stations: Sequence[WeatherStation],
) -> bytes:
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["Normal"]

    story = []

    story.append(
        Paragraph(
            "ATMOSYNC Weekly Weather Report",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"{start_date.strftime('%B %d, %Y')} – "
            f"{end_date.strftime('%B %d, %Y')}",
            normal_style,
        )
    )

    story.append(Spacer(1, 8 * mm))

    observations_by_station = defaultdict(list)

    for observation in observations:
        observations_by_station[
            observation.climate_identifier
        ].append(observation)

    for station_index, station in enumerate(stations):
        station_observations = observations_by_station.get(
            station.climate_identifier,
            [],
        )

        story.append(
            Paragraph(
                station.city,
                heading_style,
            )
        )

        story.append(
            Paragraph(
                f"Climate ID: {station.climate_identifier}",
                normal_style,
            )
        )

        story.append(Spacer(1, 3 * mm))

        table_data = [
            [
                "Date",
                "Mean °C",
                "Min °C",
                "Max °C",
                "Precip.",
                "Rain",
                "Snow",
                "Snow Ground",
            ]
        ]

        for observation in station_observations:
            table_data.append(
                [
                    observation.observation_date.strftime("%b %d"),
                    _format_value(observation.mean_temperature),
                    _format_value(observation.min_temperature),
                    _format_value(observation.max_temperature),
                    _format_value(observation.total_precipitation),
                    _format_value(observation.total_rain),
                    _format_value(observation.total_snow),
                    _format_value(observation.snow_on_ground),
                ]
            )

        if not station_observations:
            table_data.append(
                [
                    "No data",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                ]
            )

        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[
                22 * mm,
                22 * mm,
                20 * mm,
                20 * mm,
                20 * mm,
                18 * mm,
                18 * mm,
                25 * mm,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.lightgrey,
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.black,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "ALIGN",
                        (1, 1),
                        (-1, -1),
                        "RIGHT",
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (0, -1),
                        "LEFT",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, 0),
                        5,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, 0),
                        5,
                    ),
                ]
            )
        )

        story.append(table)

        if station_index < len(stations) - 1:
            story.append(PageBreak())

    document.build(story)

    return buffer.getvalue()
