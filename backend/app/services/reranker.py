from sentence_transformers import CrossEncoder

from app.core.config import settings

# Loads once per worker process.
reranker = CrossEncoder(settings.cross_encoder_model)


def rerank_chunks(
    question: str,
    chunks: list[dict],
    top_k: int = 5,
) -> list[dict]:
    if not chunks:
        return []

    pairs = [
        (question, chunk["text"])
        for chunk in chunks
    ]
    scores = reranker.predict(pairs)

    ranked = []
    for chunk, score in zip(chunks, scores):
        item = dict(chunk)
        item["rerank_score"] = float(score)
        ranked.append(item)

    ranked.sort(
        key=lambda item: item["rerank_score"],
        reverse=True,
    )
    return ranked[:top_k]
