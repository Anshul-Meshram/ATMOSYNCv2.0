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
| `GET` | `/api/weather/forecast?station=...` | Returns 7-day LightGBM predicted temperatures and precipitation |
| `POST` | `/api/rag/explain` | Generates a cited scientific climate explanation grounded in Qdrant documents |
| `GET` | `/api/health` | Health check endpoint |

---

## 3. Frontend Features

- **Interactive 7-Day Forecast Chart**: High/low temperature trends and precipitation bars powered by Chart.js.
- **Station Selector**: Switch between Toronto, Montreal, Vancouver, Calgary, Edmonton, Ottawa, Winnipeg, Quebec City, and Halifax.
- **Grounded AI Climate Assistant**: Ask natural-language climate questions with automatic Qdrant semantic retrieval, Gemini 2.5 Flash reasoning, and source citations (IPCC reports and Canadian climate studies).

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

The forecast fallback also requests historical weather from
`ATMOSYNC_WEATHER_API_BASE_URL` (defaults to the currently configured
`https://atmosyncv2-0.onrender.com`). Set that variable to the URL of your
deployed weather API if it differs. On Render's free instance, the app may run
out of memory while loading its embedding and forecasting models; use a
memory-appropriate paid instance if that happens.
