# Atmosync Weather Data Pipeline

Weather data ingestion pipeline for the Atmosync project.

The pipeline retrieves daily weather observations from Environment and Climate Change Canada (ECCC), normalizes the data, stores it in PostgreSQL, and exposes it through a FastAPI API.

## Architecture

             ECCC API
                │
                ▼
        Ingestion Service
          │            │
       normalize      upsert
          │            │
          └──────┬─────┘
                 ▼
            PostgreSQL
                 │
        ┌────────┴────────┐
        ▼                 ▼
   FastAPI API        ML / RAG

The weather pipeline is designed as a handoff component for the other Atmosync modules.

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- httpx
- APScheduler
- ReportLab
- ECCC Climate Data API

## Project Structure

app/
├── api/
│   └── weather.py
├── clients/
│   └── eccc.py
├── config/
│   ├── locations.py
│   └── settings.py
├── db/
│   └── session.py
├── models/
│   ├── eccc.py
│   └── weather.py
├── repositories/
│   └── weather.py
├── scheduler/
│   └── jobs.py
├── services/
│   ├── ingestion.py
│   ├── normalizer.py
│   └── report.py
└── main.py

alembic/
tests/
pyproject.toml

## Setup

Create and activate a virtual environment if needed:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the project:

```bash
pip install -e .
```

The project requires a PostgreSQL database.

Configure the required environment variables in `.env` according to `app/config/settings.py`.

## Database

Run the Alembic migrations before using the pipeline:

```bash
alembic upgrade head
```

## Run the API

Start the FastAPI application with:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Historical Ingestion

The CLI accepts a start and end date:

```bash
python -m app.main \
    --start-date 2020-01-01 \
    --end-date 2026-09-28
```

The ingestion process:

1. Iterates through the configured weather stations.
2. Requests daily observations from ECCC.
3. Follows ECCC pagination links.
4. Normalizes ECCC observations into the Atmosync weather model.
5. Upserts observations into PostgreSQL.

The pipeline currently has a project history start date of:

2020-01-01

Station-specific availability dates are also respected.

## Configured Stations

The pipeline currently includes 9 stations:

- Toronto
- Montreal
- Vancouver
- Calgary
- Edmonton
- Ottawa
- Winnipeg
- Quebec City
- Halifax

The station configuration is defined in:

app/config/locations.py

The available stations can also be retrieved through:

GET /weather/stations

## Weather API

### Get Weather Observations

GET /weather/{city}

Example:

```bash
curl "http://127.0.0.1:8000/weather/Toronto?start_date=2026-09-28&end_date=2026-09-28"
```

### List Stations

GET /weather/stations

### Weekly Report

Generate a 7-day PDF weather report:

GET /weather/report/weekly

Example:

```bash
curl "http://127.0.0.1:8000/weather/report/weekly?start_date=2026-09-21" \
    --output weather_report_2026-09-21.pdf
```

The report contains a separate section/page for each configured station.

## Scheduled Ingestion

The application includes a daily APScheduler job.

The scheduled job runs the ingestion for the previous available calendar day.

The scheduler configuration is controlled through the application settings.

## Data Flow

ECCC
 │
 ▼
ECCCClient
 │
 ▼
ECCCObservation
 │
 ▼
Normalizer
 │
 ▼
WeatherObservation
 │
 ▼
WeatherRepository
 │
 ▼
PostgreSQL
 │
 ▼
FastAPI
 │
 ├── Weather API
 └── Weekly PDF Report

## Logging

The pipeline uses Python application logging.

Ingestion logs include:

- station
- climate identifier
- requested date range
- ingestion start/completion
- observation count
- ingestion failures

Example:

INFO | app.services.ingestion |
Ingestion completed: climate_id=6158355 observations=1

## Notes on Missing Values

ECCC fields may legitimately be unavailable for a particular observation.

For example, an observation may contain:

total_precipitation = 0.1
total_rain = null
total_snow = null
snow_on_ground = null

The pipeline preserves these missing values as `null` rather than converting them to zero.

This prevents the pipeline from inventing values that were not supplied by ECCC.

## Handoff to Other Atmosync Modules

The weather pipeline provides weather data through the FastAPI API and PostgreSQL database.

Other modules such as ML and RAG can consume the weather data through the agreed API/database interface without depending on the internal ingestion implementation.

The main API endpoints are:

GET /weather/stations
GET /weather/{city}
GET /weather/report/weekly

The ingestion pipeline is responsible for retrieving and storing weather data; ML/RAG processing is outside the scope of this component.

