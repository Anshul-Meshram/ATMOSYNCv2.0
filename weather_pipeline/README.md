# Atmosync Weather Data Pipeline

Weather data ingestion pipeline for the Atmosync project.

The pipeline retrieves daily weather observations from Environment and Climate Change Canada (ECCC), normalizes the data, stores it in PostgreSQL, and exposes it through a FastAPI API.

## Architecture

             ECCC API
                │
                ▼
        GitHub Actions
        Daily Ingestion
                │
                ▼
           Supabase DB
                │
        ┌───────┴────────┐
        ▼                ▼
   Render API       Weekly Report
        │             Workflow
        │                │
        ▼                ▼
   ML / RAG       Supabase Storage
                         │
                         ▼
                    RAG / Reports

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
- GitHub Actions
- Supabase
- Render

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

.github/
└── workflows/
    ├── daily-ingestion.yml
    └── weekly-report.yml

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

## Run the API Locally

Start the FastAPI application with:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

The local API is available at:

```text
http://127.0.0.1:8000
```

FastAPI interactive documentation is also available at:

```text
http://127.0.0.1:8000/docs
```

## Production API

The weather pipeline is deployed as a public FastAPI service on Render.

Base URL:

```text
https://atmosyncv2-0.onrender.com
```

### Health Check

```text
GET /health
```

Example:

```bash
curl https://atmosyncv2-0.onrender.com/health
```

### List Stations

```text
GET /weather/stations
```

Example:

```bash
curl https://atmosyncv2-0.onrender.com/weather/stations
```

### Get Weather Observations

```text
GET /weather/{city}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

Example:

```bash
curl "https://atmosyncv2-0.onrender.com/weather/Toronto?start_date=2026-09-28&end_date=2026-09-28"
```

### Weekly Report

```text
GET /weather/report/weekly?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

Example:

```bash
curl "https://atmosyncv2-0.onrender.com/weather/report/weekly?start_date=2026-09-21&end_date=2026-09-27" \
    --output weather_report_2026-09-21_2026-09-27.pdf
```

The report contains a separate section/page for each configured station.

Interactive API documentation is available at:

```text
https://atmosyncv2-0.onrender.com/docs
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

```text
app/config/locations.py
```

The available stations can also be retrieved through:

```text
GET /weather/stations
```

## Scheduled Ingestion

Production daily ingestion is handled by GitHub Actions.

The workflow:

```text
GitHub Actions
      │
      ▼
Previous day's date
      │
      ▼
Weather ingestion
      │
      ▼
Supabase PostgreSQL
```

The daily workflow runs at 02:00 IST and ingests the previous day's weather data.

The workflow can also be triggered manually from GitHub Actions.

### APScheduler

The application also contains an in-process APScheduler implementation.

The scheduler setting is located in:

```text
app/config/settings.py
```

The setting is:

```python
enable_scheduler: bool = True
```

To enable the in-process scheduler:

```python
enable_scheduler: bool = True
```

To disable it:

```python
enable_scheduler: bool = False
```

The scheduler is currently disabled for the hosted Render API because production daily ingestion is handled by GitHub Actions.

If APScheduler is enabled, the application starts the scheduler when the FastAPI application starts.

## Weekly Report Automation

Weekly weather reports are generated automatically using GitHub Actions.

The workflow:

1. Determines the previous Monday-Sunday date range.
2. Requests the weekly report from the production FastAPI API.
3. Generates the PDF.
4. Uploads the PDF to the Supabase Storage bucket `weather-reports`.
5. Also stores the PDF as a GitHub Actions artifact.

The Supabase Storage bucket is private.

The persistent PDF storage location is:

```text
Supabase → Storage → weather-reports
```

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
Supabase PostgreSQL
 │
 ▼
FastAPI / Render
 │
 ├── Weather API
 └── Weekly PDF Report
          │
          ▼
   Supabase Storage

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

```text
INFO | app.services.ingestion |
Ingestion completed: climate_id=6158355 observations=1
```

## Notes on Missing Values

ECCC fields may legitimately be unavailable for a particular observation.

For example, an observation may contain:

```text
total_precipitation = 0.1
total_rain = null
total_snow = null
snow_on_ground = null
```

The pipeline preserves these missing values as `null` rather than converting them to zero.

This prevents the pipeline from inventing values that were not supplied by ECCC.

## Handoff to Other Atmosync Modules

The weather pipeline provides weather data through the public FastAPI API and the shared PostgreSQL database.

Other modules such as ML and RAG can consume the weather data through the agreed API/database interface without depending on the internal ingestion implementation.

### Production API

Base URL:

```text
https://atmosyncv2-0.onrender.com
```

Main endpoints:

```text
GET /health
GET /weather/stations
GET /weather/{city}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
GET /weather/report/weekly?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

The ingestion pipeline is responsible for retrieving and storing weather data; ML/RAG processing is outside the scope of this component.

## Accessing Supabase Data

The production weather data and generated weekly reports are stored in Supabase.

### View Weather Database

In the Supabase dashboard:

```text
Supabase
  → Table Editor
  → public
  → weather_observations
```

This table contains the stored weather observations.

### View Weekly PDF Reports

In the Supabase dashboard:

```text
Supabase
  → Storage
  → weather-reports
```

The generated weekly PDF reports are stored in this bucket.

The `weather-reports` bucket is private.

## Production Automation Summary

```text
                    ECCC
                     │
                     ▼
              GitHub Actions
              Daily Ingestion
                     │
                     ▼
             Supabase PostgreSQL
                     │
                     ▼
               Render FastAPI
                     │
              ┌──────┴──────┐
              ▼             ▼
             ML            RAG


Weekly Report:

             Render FastAPI
                    │
                    ▼
             GitHub Actions
                    │
                    ▼
             Weekly PDF
                    │
                    ▼
          Supabase Storage
           weather-reports
                    │
                    ▼
                   RAG

