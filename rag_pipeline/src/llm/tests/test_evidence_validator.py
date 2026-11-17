
from src.llm.generation.evidence_validator import has_usable_evidence


def main():
    # Case 1: Missing context
    assert has_usable_evidence(None) is False

    # Case 2: Empty results
    assert has_usable_evidence({"results": []}) is False

    # Case 3: Missing results field
    assert has_usable_evidence({}) is False

    # Case 4: Empty evidence text
    assert has_usable_evidence({
        "results": [
            {"content": "   "}
        ]
    }) is False

    # Case 5: Invalid result entry
    assert has_usable_evidence({
        "results": ["invalid entry"]
    }) is False

    # Case 6: Valid evidence
    assert has_usable_evidence({
        "results": [
            {
                "content": "Historical climate data shows rising temperatures.",
                "source": "climate_report.pdf",
                "page": 12,
            }
        ]
    }) is True

    # Case 7: One invalid result followed by valid evidence
    assert has_usable_evidence({
        "results": [
            {"content": ""},
            {
                "content": "Evidence about a climate anomaly.",
                "source": "research_paper.pdf",
            },
        ]
    }) is True

    print("Evidence validator test: SUCCESS")


if __name__ == "__main__":
    main()
