from __future__ import annotations

from typing import Any
from src.llm.prompts.system_prompt import SYSTEM_PROMPT


def format_ml_context_section(ml_data: Any) -> str:
    """Format ML forecast rows and anomalies into a readable table."""
    if not ml_data:
        return "No ML quantitative forecast data is available for this station or period."

    lines = []
    if isinstance(ml_data, dict):
        station = ml_data.get("station", "Designated Station")
        lines.append(f"Station: {station}")
        model_info = f"Model: {ml_data.get('model_name', 'LightGBM')} ({ml_data.get('model_version', 'lightgbm-v1')})"
        lines.append(model_info)

        forecasts = ml_data.get("forecasts", [])
        if isinstance(forecasts, list) and forecasts:
            lines.append("\n7-Day Numerical Forecast:")
            lines.append("| Date | Min Temp (°C) | Mean Temp (°C) | Max Temp (°C) | Precip (mm) |")
            lines.append("|---|---|---|---|---|")
            for f in forecasts:
                d = f.get("forecast_date", "N/A")
                t_min = f.get("min_temp_c", f.get("predicted_min_temp_c", "N/A"))
                t_mean = f.get("mean_temp_c", f.get("predicted_mean_temp_c", "N/A"))
                t_max = f.get("max_temp_c", f.get("predicted_max_temp_c", "N/A"))
                p = f.get("precip_mm", f.get("predicted_precip_mm", "N/A"))
                lines.append(f"| {d} | {t_min} | {t_mean} | {t_max} | {p} |")

        anomalies = ml_data.get("anomalies", [])
        if isinstance(anomalies, list) and anomalies:
            lines.append("\nDetected Anomalies (|z| >= 2.0 against 30-year station normal):")
            for a in anomalies:
                var = a.get("variable", "weather variable")
                score = a.get("anomaly_score", "N/A")
                label = a.get("label", a.get("status", "anomaly"))
                val = a.get("value", a.get("forecast_value", "N/A"))
                base = a.get("expected_baseline", "N/A")
                lines.append(f"- Date {a.get('date', a.get('forecast_date'))}: {var} = {val} vs baseline {base} (score: {score}, label: {label})")

    elif isinstance(ml_data, list):
        lines.append(str(ml_data))
    else:
        lines.append(str(ml_data))

    return "\n".join(lines)


def format_rag_context_section(rag_data: Any) -> str:
    """Format retrieved literature passages with source and page attribution."""
    if not rag_data:
        return "No relevant scientific documents found in vector store."

    chunks = []
    if isinstance(rag_data, dict):
        chunks = rag_data.get("results", rag_data.get("chunks", []))
    elif isinstance(rag_data, list):
        chunks = rag_data

    if not chunks:
        return "No relevant scientific documents found in vector store."

    lines = []
    for i, c in enumerate(chunks, start=1):
        if hasattr(c, "document_name"):
            doc = c.document_name
            page = c.page
            score = getattr(c, "score", None)
            text = c.text
        elif isinstance(c, dict):
            doc = c.get("document_name") or c.get("source", "Unknown Document")
            page = c.get("page", "N/A")
            score = c.get("score")
            text = c.get("text") or c.get("content", "")
        else:
            doc, page, score, text = "Unknown", "N/A", None, str(c)

        score_str = f", Score: {score:.4f}" if score is not None else ""
        lines.append(f"--- Document [{i}]: {doc} (Page: {page}{score_str}) ---")
        lines.append(text.strip())
        lines.append("")

    return "\n".join(lines)


def build_prompt(
    user_query: str,
    ml_context: Any = None,
    rag_context: Any = None,
) -> str:
    """
    Build the complete prompt sent to the LLM assistant, strictly partitioning
    the sections and enforcing evidence-based reasoning.
    """
    parts = [
        SYSTEM_PROMPT.strip(),
        "\n\n==========================================",
        "USER QUERY:",
        "==========================================",
        user_query.strip(),
        "\n\n==========================================",
        "ML CONTEXT (Empirical Forecast & Anomalies):",
        "==========================================",
        format_ml_context_section(ml_context),
        "\n\n==========================================",
        "RETRIEVED RAG EVIDENCE (Scientific Documents):",
        "==========================================",
        format_rag_context_section(rag_context),
        "\n\n==========================================",
        "INSTRUCTIONS FOR YOUR RESPONSE:",
        "==========================================",
        "1. Answer the query thoroughly, synthesising BOTH the ML numbers and RAG evidence.",
        "2. Cite documents explicitly as [Document Name, p. X]. Never invent citations.",
        "3. If ML data or RAG evidence is noted as unavailable or insufficient, acknowledge it explicitly.",
        "4. Output clear, professional markdown.",
    ]

    return "\n".join(parts)
