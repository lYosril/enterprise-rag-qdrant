from scripts.evaluate_configs import (
    ABSTENTION_INDICATORS,
    citation_structural_validity,
    fact_coverage,
    looks_abstained,
    percentile,
    retrieval_metrics,
)


def test_retrieval_metrics_page_recall_and_hit():
    sources = [
        {"document": "handbook.pdf", "page": 2, "score": 0.9},
        {"document": "handbook.pdf", "page": 5, "score": 0.8},
        {"document": "other.pdf", "page": 5, "score": 0.7},
    ]
    recall, hit, mrr = retrieval_metrics(
        sources, expected_document="handbook.pdf", expected_pages=[2, 4], k=5
    )
    assert recall == 0.5  # page 2 matches, page 4 missing
    assert hit is True
    assert mrr == 1.0  # first relevant is rank 1


def test_retrieval_metrics_mrr_second_match():
    sources = [
        {"document": "other.pdf", "page": 10, "score": 0.9},
        {"document": "handbook.pdf", "page": 4, "score": 0.8},
    ]
    recall, hit, mrr = retrieval_metrics(
        sources, expected_document="handbook.pdf", expected_pages=[4], k=5
    )
    assert hit is True
    assert mrr == 0.5  # second rank


def test_retrieval_metrics_no_expected_returns_zero():
    sources = [{"document": "handbook.pdf", "page": 2}]
    recall, hit, mrr = retrieval_metrics(sources, expected_document=None, expected_pages=[], k=5)
    assert (recall, hit, mrr) == (0.0, False, 0.0)


def test_fact_coverage_empty_expected_returns_none():
    assert fact_coverage("anything", []) is None


def test_fact_coverage_counts_matches_case_insensitively():
    answer = "The policy covers race, religion and national origin."
    expected = ["race", "religion", "age"]  # age not present
    assert fact_coverage(answer, expected) == 2 / 3


def test_looks_abstained():
    for phrase in ABSTENTION_INDICATORS:
        # Many indicators contain contractions/spaces; test a plausible form
        answer = f"I {phrase} the information you requested."
        assert looks_abstained(answer) is True

    assert looks_abstained("Yes, the document states X.") is False


def test_citation_structural_validity():
    valid = {("doc.pdf", 1), ("doc.pdf", 2)}
    sources = [{"document": "doc.pdf", "page": 1}, {"document": "doc.pdf", "page": 99}]
    assert citation_structural_validity(sources, valid) == 0.5
    assert citation_structural_validity([], valid) == 1.0


def test_percentile():
    values = [1, 2, 3, 4, 5]
    assert percentile(values, 0.5) == 3.0
    assert percentile([], 0.5) == 0.0
    assert percentile([10], 0.9) == 10.0
    # p95 for 5 items: rank=(5-1)*0.95=3.8, so linear interp between idx3 (value 4) and idx4 (value 5): 4*0.2+5*0.8=4.8
    assert round(percentile(values, 0.95), 1) == 4.8
