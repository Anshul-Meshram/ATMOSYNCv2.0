# AtmoSync Full-Stack Dashboard & API Gateway

This module hosts the interactive web dashboard and the unified API gateway bridging:
- **Weather Pipeline**: Canadian station observations from Environment and Climate Change Canada (ECCC).
- **Machine Learning Layer**: 7-day LightGBM weather forecasts.
- **RAG Pipeline**: Grounded, cited climate intelligence powered by Qdrant and Google Gemini.

---

## 1. Quick Start

Run the full-stack server from the project root:

```bash
python frontend_backend/server.py
```

Then open your browser at:
👉 **`http://localhost:8000`**

---

## 2. Available API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the interactive AtmoSync Climate Dashboard |
| `GET` | `/api/weather/stations` | Returns monitored Canadian weather stations |
| `GET` | `/api/weather/current?station=...` | Returns current Open-Meteo weather conditions and today's estimated low/high |
| `GET` | `/api/weather/forecast?station=...` | Returns 7-day LightGBM predicted temperatures and precipitation with the generation timestamp |
| `GET` | `/api/weather/calendar?station=...&date=YYYY-MM-DD` | Returns date-specific ECCC observations, current conditions, or separate provider/LightGBM forecasts |
| `POST` | `/api/rag/explain` | Generates a cited scientific climate explanation grounded in Qdrant documents |
| `GET` | `/api/health` | Health check endpoint |

---

## 3. Frontend Features

- **Interactive 7-Day Forecast Chart**: High/low temperature trends and precipitation bars powered by Chart.js.
- **Station Selector**: Switch between Toronto, Montreal, Vancouver, Calgary, Edmonton, Ottawa, Winnipeg, Quebec City, and Halifax.
- **Timezone-Aware Weather Date Picker**: Choose a date from the native date picker. Historical results retain only ECCC actuals; today uses Open-Meteo current estimates; future dates show Open-Meteo and LightGBM results separately.
- **Source Transparency**: Current source timestamps, retrieval times, LightGBM forecast generation time, forecast/model labels, and missing-data states are shown instead of substituting forecast values for historical observations.
- **Selected-Date Tools**: Explain the selected date through the existing RAG endpoint and export available values as CSV. Stored forecast anomaly flags are shown only for the matching forecast date and are not official weather warnings.
- **Theme Preference**: Toggle dark/light appearance; the preference is stored in the browser.
- **Grounded AI Climate Assistant**: Ask natural-language climate questions with automatic Qdrant semantic retrieval, Gemini 2.5 Flash reasoning, and source citations (IPCC reports and Canadian climate studies).

The historical observations in this calendar are daily, not hourly. The dashboard
gateway reads them from the configured weather API (`/weather/{city}`). Set
`ATMOSYNC_OBSERVATIONS_API_BASE_URL` to that service's base URL when it differs
from the default. `ATMOSYNC_WEATHER_API_BASE_URL` is also accepted as a fallback
and is used by LightGBM inference. If the upstream response includes
`field_sources`, values marked as forecast-derived are omitted from historical
results. A successful but empty response is shown as “no observations”; an
upstream request failure is shown as an error rather than replaced with
synthetic data.

## 4. Deploying on Render

The repository-root `render.yaml` deploys this dashboard and API gateway as one
Render web service. In Render, choose **New + → Blueprint**, connect this
GitHub repository, and select the branch to deploy. Render will use
`requirements-render.txt` and start the Flask app with Gunicorn.

Set `GEMINI_API_KEY` in the service's **Environment** settings to enable live
Gemini answers. Without it, the RAG service uses its mock provider. The service
uses the local Qdrant collection and SQLite forecast cache in the repository;
Render's local filesystem is ephemeral, so runtime changes to those files do
not survive a new deploy or instance replacement. Use managed/persistent storage
if runtime-written data must be retained.

The date calendar's ECCC history requests and the forecast fallback use the
weather API base URL. Set `ATMOSYNC_OBSERVATIONS_API_BASE_URL` to the deployed
service that exposes `/weather/{city}`; if unset, the dashboard falls back to
`ATMOSYNC_WEATHER_API_BASE_URL` and then the existing configured default
`https://atmosyncv2-0.onrender.com`. On Render's free instance, the app may run
out of memory while loading its embedding and forecasting models; use a
memory-appropriate paid instance if that happens.
