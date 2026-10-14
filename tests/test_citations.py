"""
Tests for citation extraction, citation validation, and source alignment.
"""

from app.services.citation_service import validate_sources


def test_validate_sources_matches_retrieved_evidence():
    sources = [
        {
            "document_id": "b79afc05-d43a-4246-9a6f-a1f7b6a30e11",
            "document": "employee_handbook.pdf",
            "page": 4,
            "text": "Employment is at will.",
            "score": 0.95,
        },
        {
            "document_id": "b79afc05-d43a-4246-9a6f-a1f7b6a30e11",
            "document": "employee_handbook.pdf",
            "page": 5,
            "text": "The company is an equal opportunity employer.",
            "score": 0.88,
        },
    ]

    # Valid citations matching real retrieved sources
    cited = [
        {"document_id": "b79afc05-d43a-4246-9a6f-a1f7b6a30e11", "page": 4},
        {"document_id": "b79afc05-d43a-4246-9a6f-a1f7b6a30e11", "page": 5},
    ]

    valid = validate_sources(sources, cited)
    assert len(valid) == 2


def test_validate_sources_rejects_hallucinated_citations():
    sources = [
        {
            "document_id": "b79afc05-d43a-4246-9a6f-a1f7b6a30e11",
            "document": "employee_handbook.pdf",
            "page": 4,
            "text": "Employment is at will.",
            "score": 0.95,
        }
    ]

    # Hallucinated citation with non-existent page 99
    fake_cited = [
        {"document_id": "b79afc05-d43a-4246-9a6f-a1f7b6a30e11", "page": 99},
        {"document_id": "00000000-0000-0000-0000-000000000000", "page": 1},
    ]

    valid = validate_sources(sources, fake_cited)
    assert len(valid) == 0


def test_validate_sources_handles_empty_sources():
    valid = validate_sources([], [{"document_id": "abc", "page": 1}])
    assert valid == []
