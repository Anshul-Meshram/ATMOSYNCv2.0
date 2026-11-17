from src.llm.clients.llm_provider import LLMProvider
from src.llm.services.llm_service import ClimateRAGService


class MockLLMProvider(LLMProvider):
    def __init__(self):
        self.last_prompt = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return (
            "Based on the Canadian climate records, the forecasted warming trend "
            "exceeds seasonal baselines for this region [Climate_Intelligence_System_Project_Report.pdf]."
        )


def test_explain_climate_event_with_mock():
    mock_provider = MockLLMProvider()
    service = ClimateRAGService(provider=mock_provider)

    ml_context = {
        "event": {"type": "heatwave", "severity": "high"},
        "confidence": 0.92,
    }

    response = service.explain_climate_event(
        user_query="What causes severe heatwaves in Canada?",
        ml_context=ml_context,
        top_k=3,
    )

    assert response.answer is not None
    assert response.grounded is True
    assert response.confidence == 0.92
    assert response.event_summary is not None
    assert response.event_summary.event_type == "heatwave"
    assert len(response.citation) > 0
    assert any(c.source for c in response.citation)

    print("Test explain_climate_event: PASS")


def test_explain_ml_forecast_contract():
    """Verify integration with the ML teammate's LightGBM API response contract."""
    mock_provider = MockLLMProvider()
    service = ClimateRAGService(provider=mock_provider)

    ml_forecast_payload = {
        "station": "toronto",
        "model": "LightGBM",
        "history_start": "2026-08-05",
        "history_end": "2026-11-02",
        "forecast_horizon_days": 7,
        "predictions": [
            {
                "forecast_date": "2026-11-03",
                "forecast_horizon_day": 1,
                "predicted_min_temp_c": 5.2,
                "predicted_mean_temp_c": 8.9,
                "predicted_max_temp_c": 12.5,
                "predicted_precip_mm": 2.4,
            },
            {
                "forecast_date": "2026-11-04",
                "forecast_horizon_day": 2,
                "predicted_min_temp_c": 6.0,
                "predicted_mean_temp_c": 9.5,
                "predicted_max_temp_c": 13.0,
                "predicted_precip_mm": 0.0,
            },
        ],
    }

    response = service.explain_ml_forecast(
        forecast_data=ml_forecast_payload,
        custom_query="Explain whether the forecasted rain and temperatures in Toronto match seasonal climate data.",
        top_k=3,
    )

    assert response.answer is not None
    assert response.grounded is True
    assert "toronto" in mock_provider.last_prompt.lower()
    assert "LightGBM" in mock_provider.last_prompt
    assert len(response.citation) > 0

    print("Test explain_ml_forecast: PASS")


def main():
    print("=" * 60)
    print("TESTING CLIMATE RAG SERVICE (ML + RAG INTEGRATION)")
    print("=" * 60)

    test_explain_climate_event_with_mock()
    test_explain_ml_forecast_contract()

    print("\nAll Climate RAG Service tests PASSED successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
