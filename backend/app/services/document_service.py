
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

from app.core.config import settings
from app.models.models import Document


DOCUMENT_DIR = Path("data/documents")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Load the embedding model once per backend process.
embedding_model = SentenceTransformer(settings.embedding_model)

qdrant = QdrantClient(url=settings.qdrant_url)


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
    ensure_collection()

    reader = PdfReader(str(pdf_path))
    points = []

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

        for chunk, embedding in zip(chunks, embeddings):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding.tolist(),
                    payload={
                        "document_id": str(document.id),
                        # Keep both keys for compatibility with older code/data.
                        "document": document.filename,
                        "filename": document.filename,
                        "page": page_number,
                        "text": chunk,
                    },
                )
            )

    if not points:
        raise ValueError(
            "No extractable text found in the PDF. "
            "Scanned PDFs require OCR."
        )

    # Upload in batches instead of sending every vector at once.
    for start in range(0, len(points), 64):
        qdrant.upsert(
            collection_name=settings.qdrant_collection,
            points=points[start:start + 64],
            wait=True,
        )

    document.chunk_count = len(points)
    document.status = "indexed"
    db.commit()
    db.refresh(document)

    return len(points)


def delete_document_vectors(document_id: uuid.UUID):
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