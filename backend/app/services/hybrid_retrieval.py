from app.core.config import settings


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    k: int | None = None,
) -> list[tuple[str, float]]:
    """Merge ranked chunk-id lists using Reciprocal Rank Fusion."""
    smoothing = k if k is not None else settings.rrf_k
    fused_scores: dict[str, float] = {}

    for ranked_ids in ranked_lists:
        for rank, chunk_id in enumerate(ranked_ids, start=1):
            fused_scores[chunk_id] = (
                fused_scores.get(chunk_id, 0.0)
                + 1.0 / (smoothing + rank)
            )

    return sorted(
        fused_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )
