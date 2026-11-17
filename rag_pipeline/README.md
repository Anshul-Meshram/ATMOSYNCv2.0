# AtmoSync RAG & LLM Pipeline

The **RAG & LLM Pipeline** is the decision-support and explainability engine of the AtmoSync Climate Intelligence System. It couples quantitative predictions from the Machine Learning layer (LightGBM forecaster) with grounded scientific climate literature (IPCC reports, Environment and Climate Change Canada studies) using semantic search and Google Gemini.

---

## 1. Architecture Overview

```
                      +-----------------------------+
                      |   ML Module (LightGBM API)  |
                      |  /predict & /forecasts JSON |
                      +--------------+--------------+
                                     |
                                     v
+------------------+     +-----------+-------------+     +-------------------+
| Climate Document | --> |   Qdrant Vector Store   | --> | Evidence Validator|
| PDFs & Reports   |     | (384-dim, MiniLM-L6-v2) |     |  (Zero Speculation|
+------------------+     +-----------+-------------+     +---------+---------+
                                     |                             |
                                     v                             v
                        +------------+-----------------------------+---------+
                        |                 Context Assembler                  |
                        |      (System Directives + ML Data + Evidence)      |
                        +----------------------------+-----------------------+
                                                     |
                                                     v
                                       +-------------+--------------+
                                       |      Google Gemini LLM     |
                                       |  (gemini-2.5-flash Client) |
                                       +-------------+--------------+
                                                     |
                                                     v
                                       +-------------+--------------+
                                       | Standardized LLMResponse   |
                                       | (Cited Scientific Insight) |
                                       +----------------------------+
```

---

## 2. Directory Structure

```
rag_pipeline/
├── qdrant_storage/                 # Local embedded Qdrant vector database
│   └── collection/climate_documents/
├── src/
│   ├── llm/
│   │   ├── clients/
│   │   │   ├── gemini_client.py    # Gemini client with exponential backoff retry logic
│   │   │   └── llm_provider.py    # Abstract base provider interface
│   │   ├── context/
│   │   │   └── assembler.py        # Validates request and builds prompt
│   │   ├── generation/
│   │   │   ├── evidence_validator.py # Confirms presence of retrieved literature
│   │   │   └── generation_service.py # Provider-agnostic generation orchestrator
│   │   ├── prompts/
│   │   │   ├── prompt_builder.py   # Assembles system prompt, query, ML & RAG data
│   │   │   └── system_prompt.py    # 10 strict anti-hallucination scientific rules
│   │   ├── schemas/
│   │   │   ├── request.py          # LLMRequest dataclass
│   │   │   └── response.py         # LLMResponse, Citation, EventSummary dataclasses
│   │   ├── services/
│   │   │   └── llm_service.py      # ClimateRAGService: high-level end-to-end coordinator
│   │   └── tests/                  # Unit and integration test suite
│   │       ├── test_climate_rag_service.py
│   │       ├── test_context_assembler.py
│   │       ├── test_context_validation.py
│   │       ├── test_evidence_validator.py
│   │       ├── test_generation_services.py
│   │       ├── test_prompt_builder.py
│   │       └── test_schemas.py
│   └── rag/
│       ├── documents/              # Climate PDFs (IPCC reports, project reports)
│       ├── embeddings/
│       │   └── embedding_model.py  # sentence-transformers (all-MiniLM-L6-v2)
│       ├── ingestion/
│       │   ├── chunker.py          # Overlapping passage chunker with metadata
│       │   ├── pdf_loader.py       # PyMuPDF document loader
│       │   └── text_cleaner.py     # Text cleaning & normalization
│       ├── retrieval/
│       │   └── retriever.py        # Top-k Qdrant semantic search
│       └── vector_db/
│           ├── indexer.py          # Ingests and indexes document vectors
│           └── qdrant_client.py    # Qdrant client configuration & collection setup
└── README.md
```

---

## 3. Integration with the ML Module

The pipeline natively consumes the response contracts from the ML team's endpoints (`POST /predict` and `GET /forecasts`):

```python
from src.llm.services.llm_service import create_climate_rag_service

service = create_climate_rag_service()

# 1. Payload received from teammate's ML API (e.g., LightGBM /predict)
ml_forecast = {
    "station": "toronto",
    "model": "LightGBM",
    "predictions": [
        {
            "forecast_date": "2026-11-04",
            "predicted_min_temp_c": 5.2,
            "predicted_mean_temp_c": 8.9,
            "predicted_max_temp_c": 12.5,
            "predicted_precip_mm": 2.4,
        }
    ],
}

# 2. Generate grounded explanation
response = service.explain_ml_forecast(
    forecast_data=ml_forecast,
    custom_query="Explain whether the forecasted temperatures exceed typical seasonal baselines.",
)

print("Answer:", response.answer)
print("Citations:", response.citation)
print("Grounded:", response.grounded)
```

---

## 4. Running the Tests

To run the complete test suite across all 12 modules:

```bash
cd rag_pipeline
python -m src.llm.tests.test_climate_rag_service
python -m src.llm.tests.test_context_assembler
python -m src.llm.tests.test_context_validation
python -m src.llm.tests.test_evidence_validator
python -m src.llm.tests.test_generation_services
python -m src.llm.tests.test_prompt_builder
python -m src.llm.tests.test_schemas
python -m src.rag.embeddings.test_embedding
python -m src.rag.ingestion.test_chunker
python -m src.rag.retrieval.test_retriever
python -m src.rag.vector_db.test_qdrant
python -m src.rag.vector_db.test_indexer
```

All 12 tests run with zero failures and operate smoothly in offline environments.
