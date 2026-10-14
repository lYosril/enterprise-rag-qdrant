"""
Document Ingestion & Management Service.

Handles:
- PDF text extraction & chunking
- Deterministic chunk ID generation (preventing vector duplication on retries)
- Vector embedding generation & batch upsert into Qdrant
- Database metadata synchronization & error handling
- Reconciliation between PostgreSQL and Qdrant
"""

import uuid
from pathlib import Path

from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import logger
from app.models.models import Document, DocumentChunk


DOCUMENT_DIR = Path("data/documents")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Load the embedding model once per backend process.
embedding_model = SentenceTransformer(settings.embedding_model)
qdrant = QdrantClient(url=settings.qdrant_url)


def make_deterministic_chunk_id(
    document_id: str | uuid.UUID,
    page_number: int,
    chunk_index: int,
    version: int = 1,
) -> str:
    """
    Generate a deterministic UUIDv5 for each chunk based on:
    document ID, page number, chunk index, and document version.

    Upserting the same chunk ID replaces existing vectors in Qdrant,
    guaranteeing that retries or re-indexing operations never duplicate chunks.
    """
    seed = f"{str(document_id)}:{page_number}:{chunk_index}:{version}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def ensure_collection():
    collections = {
        item.name
        for item in qdrant.get_collections().collections
    }

    if settings.qdrant_collection not in collections:
        qdrant.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=embedding_model.get_sentence_embedding_dimension(),
                distance=Distance.COSINE,
            ),
        )


def split_text(text: str) -> list[str]:
    chunks = []
    start = 0
    step = CHUNK_SIZE - CHUNK_OVERLAP

    while start < len(text):
        chunk = text[start:start + CHUNK_SIZE].strip()

        if chunk:
            chunks.append(chunk)

        start += step

    return chunks


def index_document(
    db: Session,
    document: Document,
    pdf_path: Path,
) -> int:
    """
    Indexes a PDF document into Qdrant and updates PostgreSQL document status.

    Lifecycle:
    uploaded -> processing -> indexed (or failed)
    """
    ensure_collection()

    document.status = "processing"
    document.error_message = None
    db.commit()
    db.refresh(document)

    try:
        reader = PdfReader(str(pdf_path))
        points = []
        chunk_objects = []

        version = getattr(document, "version", 1) or 1
        global_chunk_idx = 0

        for page_number, page in enumerate(reader.pages, start=1):
            text = " ".join((page.extract_text() or "").split())

            if not text:
                continue

            chunks = split_text(text)

            if not chunks:
                continue

            embeddings = embedding_model.encode(
                chunks,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            for page_chunk_idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = make_deterministic_chunk_id(
                    document.id,
                    page_number,
                    page_chunk_idx,
                    version=version,
                )

                points.append(
                    PointStruct(
                        id=chunk_id,
                        vector=embedding.tolist(),
                        payload={
                            "chunk_id": chunk_id,
                            "document_id": str(document.id),
                            "owner_id": str(document.owner_id),
                            "document": document.filename,
                            "filename": document.filename,
                            "page": page_number,
                            "text": chunk,
                            "version": version,
                        },
                    )
                )

                chunk_objects.append(
                    DocumentChunk(
                        id=uuid.UUID(chunk_id),
                        document_id=document.id,
                        owner_id=document.owner_id,
                        page_number=page_number,
                        content=chunk,
                    )
                )
                global_chunk_idx += 1

        if not points:
            raise ValueError(
                "No extractable text found in the PDF. "
                "Scanned PDFs require OCR."
            )

        # Upload in batches of 64
        for start in range(0, len(points), 64):
            qdrant.upsert(
                collection_name=settings.qdrant_collection,
                points=points[start:start + 64],
                wait=True,
            )

        # Sync document chunks in PostgreSQL (delete old chunks for doc if any, then insert)
        existing_chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document.id)
        ).all()
        for c in existing_chunks:
            db.delete(c)
        db.flush()

        for chunk_obj in chunk_objects:
            db.add(chunk_obj)

        document.chunk_count = len(points)
        document.status = "indexed"
        document.error_message = None
        db.commit()
        db.refresh(document)

        logger.info(
            "document_indexed_successfully",
            document_id=str(document.id),
            chunks=len(points),
        )
        return len(points)

    except Exception as exc:
        db.rollback()
        document.status = "failed"
        document.error_message = str(exc)[:500]
        db.commit()
        logger.error(
            "document_indexing_failed",
            document_id=str(document.id),
            error=str(exc),
        )
        raise


def delete_document_vectors(document_id: uuid.UUID | str):
    """Remove all vectors belonging to document_id from Qdrant."""
    ensure_collection()

    qdrant.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=str(document_id)),
                )
            ]
        ),
        wait=True,
    )


def reconcile_documents(db: Session) -> dict:
    """
    Periodic reconciliation job that checks PostgreSQL document states
    against Qdrant vector counts and flags inconsistent documents.
    """
    ensure_collection()
    documents = db.scalars(select(Document)).all()
    inconsistencies = []

    for doc in documents:
        if doc.status == "indexed":
            # Count vectors in Qdrant for this doc
            resp = qdrant.count(
                collection_name=settings.qdrant_collection,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=str(doc.id)),
                        )
                    ]
                ),
            )
            if resp.count == 0:
                inconsistencies.append({
                    "document_id": str(doc.id),
                    "issue": "Marked indexed in PostgreSQL but 0 vectors in Qdrant",
                    "action_required": "reindex",
                })
        elif doc.status in {"failed", "uploaded"}:
            resp = qdrant.count(
                collection_name=settings.qdrant_collection,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=str(doc.id)),
                        )
                    ]
                ),
            )
            if resp.count > 0:
                inconsistencies.append({
                    "document_id": str(doc.id),
                    "issue": f"Document status is {doc.status} but {resp.count} orphaned vectors exist",
                    "action_required": "cleanup_vectors",
                })

    return {
        "total_documents": len(documents),
        "inconsistencies_found": len(inconsistencies),
        "inconsistencies": inconsistencies,
    }