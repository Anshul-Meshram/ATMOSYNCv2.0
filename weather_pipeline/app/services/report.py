from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime, timezone
import hashlib
from io import BytesIO
import json
import logging
import os
from pathlib import Path
from typing import Any, Sequence

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

logger = logging.getLogger(__name__)

# Default directory for persisted reports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS_DIR = Path(
    os.getenv("ATMOSYNC_REPORTS_DIR", PROJECT_ROOT / "data" / "reports")
)

# Registry for report generation event hooks (e.g. for RAG auto-ingestion)
REPORT_GENERATED_HOOKS: list[Callable[[Path, dict[str, Any]], Any]] = []


def register_report_hook(hook: Callable[[Path, dict[str, Any]], Any]) -> None:
    """Register a callback to be notified when a report is saved."""
    if hook not in REPORT_GENERATED_HOOKS:
        REPORT_GENERATED_HOOKS.append(hook)


def emit_report_generated(report_path: Path, metadata: dict[str, Any]) -> None:
    """Notify all registered hooks about a newly generated report."""
    for hook in REPORT_GENERATED_HOOKS:
        try:
            hook(report_path, metadata)
        except Exception as exc:
            logger.exception("Report generation hook %r failed: %s", hook, exc)


def _auto_register_default_hooks():
    try:
        import sys
        rag_root = PROJECT_ROOT.parent / "rag_pipeline"
        if rag_root.exists() and str(rag_root) not in sys.path:
            sys.path.insert(0, str(rag_root))
        from src.rag.ingestion.auto_ingest import weather_report_auto_ingest_hook
        register_report_hook(weather_report_auto_ingest_hook)
    except Exception as exc:
        logger.debug("Auto-register RAG hook skipped: %s", exc)


_auto_register_default_hooks()


def get_report_filename(start_date: date, end_date: date) -> str:
    """Return a deterministic filename for the 7-day weather report."""
    return f"weather_report_{start_date.isoformat()}_{end_date.isoformat()}.pdf"


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
        title="ATMOSYNC Weekly Weather Report",
        author="AtmoSync Weather Pipeline",
        subject=f"Weather observation report from {start_date.isoformat()} to {end_date.isoformat()}",
        creator="AtmoSync Report Generator",
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


def save_weekly_report(
    pdf_bytes: bytes,
    start_date: date,
    end_date: date,
    stations: Sequence[WeatherStation],
    output_dir: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """
    Save the generated PDF report deterministically to disk,
    create companion metadata (.meta.json), and notify registered hooks.

    Returns:
        tuple of (pdf_path, metadata_dict)
    """
    target_dir = Path(output_dir or DEFAULT_REPORTS_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = get_report_filename(start_date, end_date)
    pdf_path = target_dir / filename
    meta_path = target_dir / f"{filename}.meta.json"

    pdf_path.write_bytes(pdf_bytes)

    sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
    generated_at_iso = datetime.now(timezone.utc).isoformat()

    metadata = {
        "report_name": filename,
        "doc_type": "weather_report",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "stations": [
            {
                "city": s.city,
                "climate_identifier": s.climate_identifier,
            }
            for s in stations
        ],
        "file_size": len(pdf_bytes),
        "sha256": sha256_hash,
        "generated_at": generated_at_iso,
        "pdf_path": str(pdf_path.resolve()),
    }

    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Persisted weekly report to %s (sha256: %s)", pdf_path, sha256_hash)

    emit_report_generated(pdf_path, metadata)
    return pdf_path, metadata
