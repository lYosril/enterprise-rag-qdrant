import uuid

from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import (
    EMPTY_RETRIEVAL_TOTAL,
    RERANK_LATENCY,
    RETRIEVAL_LATENCY,
)
from app.services.document_service import (
    embedding_model,
    ensure_collection,
    qdrant,
)
from app.services.hybrid_retrieval import reciprocal_rank_fusion
from app.services.lexical_retrieval import search_lexical_chunks
from app.services.reranker import rerank_chunks


def _owner_filter(owner_id: str) -> Filter:
    return Filter(
        must=[
            FieldCondition(
                key="owner_id",
                match=MatchValue(value=owner_id),
            )
        ]
    )


def _dense_retrieve(
    question: str,
    owner_id: str,
    limit: int,
) -> list[dict]:
    ensure_collection()

    query_vector = embedding_model.encode(
        question,
        normalize_embeddings=True,
    ).tolist()

    with RETRIEVAL_LATENCY.time():
        results = qdrant.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            query_filter=_owner_filter(owner_id),
            limit=limit,
            with_payload=True,
        ).points

    candidates = []
    for result in results:
        payload = result.payload or {}
        text = payload.get("text")
        document_id = payload.get("document_id")
        if not text or not document_id:
            continue

        chunk_id = payload.get("chunk_id") or str(result.id)
        candidates.append({
            "chunk_id": str(chunk_id),
            "document_id": str(document_id),
            "document": (
                payload.get("filename")
                or payload.get("document")
                or "Unknown document"
            ),
            "page": payload.get("page"),
            "text": text,
            "score": float(result.score),
        })

    return candidates


def retrieve_ranked_chunks(
    question: str,
    owner_id: str,
    db: Session,
    *,
    use_hybrid: bool = True,
    use_rerank: bool = True,
    final_top_k: int = 5,
) -> list[dict]:
    dense_limit = settings.rag_dense_candidate_limit
    dense_candidates = _dense_retrieve(
        question,
        owner_id,
        limit=dense_limit,
    )

    if not use_hybrid:
        pool = dense_candidates
        if use_rerank and pool:
            with RERANK_LATENCY.time():
                reranked = rerank_chunks(
                    question,
                    pool,
                    top_k=final_top_k,
                )
            return _normalize_sources(reranked, score_key="rerank_score")
        return _normalize_sources(pool[:final_top_k], score_key="score")

    lexical_candidates = search_lexical_chunks(
        db,
        question,
        owner_id,
        limit=settings.rag_lexical_candidate_limit,
    )

    dense_ranking = [item["chunk_id"] for item in dense_candidates]
    lexical_ranking = [item["chunk_id"] for item in lexical_candidates]
    rank_lists = [lst for lst in (dense_ranking, lexical_ranking) if lst]

    if not rank_lists:
        EMPTY_RETRIEVAL_TOTAL.inc()
        return []

    fused = reciprocal_rank_fusion(rank_lists)
    candidate_map: dict[str, dict] = {}
    for item in dense_candidates + lexical_candidates:
        candidate_map[item["chunk_id"]] = item

    pool = []
    for chunk_id, rrf_score in fused[:dense_limit]:
        if chunk_id not in candidate_map:
            continue
        merged = dict(candidate_map[chunk_id])
        merged["score"] = float(rrf_score)
        pool.append(merged)

    if not pool:
        EMPTY_RETRIEVAL_TOTAL.inc()
        return []

    if not use_rerank:
        return _normalize_sources(pool[:final_top_k], score_key="score")

    with RERANK_LATENCY.time():
        reranked = rerank_chunks(
            question,
            pool,
            top_k=final_top_k,
        )

    return _normalize_sources(reranked, score_key="rerank_score")


def _normalize_sources(
    items: list[dict],
    score_key: str,
) -> list[dict]:
    normalized = []
    for item in items:
        source = {
            "chunk_id": item["chunk_id"],
            "document_id": item["document_id"],
            "document": item["document"],
            "page": item["page"],
            "text": item["text"],
            "score": float(item.get(score_key, item.get("score", 0.0))),
        }
        if "rerank_score" in item:
            source["rerank_score"] = float(item["rerank_score"])
        normalized.append(source)
    return normalized


def relevant_chunk_ids_for_eval(
    db: Session,
    owner_id: uuid.UUID,
    expected_document: str,
    expected_pages: list[int],
) -> set[str]:
    from sqlalchemy import select

    from app.models.models import Document, DocumentChunk

    statement = (
        select(DocumentChunk.id)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.owner_id == owner_id,
            Document.filename == expected_document,
            DocumentChunk.page_number.in_(expected_pages),
        )
    )
    return {str(chunk_id) for chunk_id in db.scalars(statement).all()}
