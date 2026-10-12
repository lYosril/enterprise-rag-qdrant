import re
import uuid

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Document, DocumentChunk


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def search_lexical_chunks(
    db: Session,
    question: str,
    owner_id: str,
    limit: int = 20,
) -> list[dict]:
    owner_uuid = uuid.UUID(owner_id)
    rows = db.execute(
        select(
            DocumentChunk,
            Document.filename,
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.owner_id == owner_uuid)
        .order_by(DocumentChunk.created_at.desc())
    ).all()

    if not rows:
        return []

    chunks = [row[0] for row in rows]
    filenames = {row[0].id: row[1] for row in rows}
    corpus = [_tokenize(chunk.content) for chunk in chunks]
    query_tokens = _tokenize(question)

    if not query_tokens:
        return []

    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query_tokens)

    ranked = sorted(
        zip(chunks, scores),
        key=lambda item: item[1],
        reverse=True,
    )[:limit]

    results = []
    for chunk, score in ranked:
        if score <= 0:
            continue
        results.append({
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "document": filenames[chunk.id],
            "page": chunk.page_number,
            "text": chunk.content,
            "score": float(score),
        })

    return results
