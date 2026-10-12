
def validate_sources(
    cited_sources: list[dict],
    retrieved_sources: list[dict],
) -> list[dict]:
    allowed = {
        (
            source.get("document_id"),
            source.get("page"),
        )
        for source in retrieved_sources
    }

    valid = []

    for citation in cited_sources:
        key = (
            citation.get("document_id"),
            citation.get("page"),
        )

        if key in allowed:
            valid.append(citation)

    return valid