from pathlib import Path

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from tqdm import tqdm


# ============================================================
# Configuration
# ============================================================

DOCUMENTS_DIR = Path("data/documents")

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "enterprise_documents"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


# ============================================================
# PDF extraction
# ============================================================

def extract_pdf_pages(pdf_path: Path):
    reader = PdfReader(str(pdf_path))

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        text = " ".join(text.split())

        if text:
            pages.append(
                {
                    "page": page_number,
                    "text": text,
                }
            )

    return pages


# ============================================================
# Text chunking
# ============================================================

def create_chunks(text: str, chunk_size: int, overlap: int):
    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


# ============================================================
# Main ingestion pipeline
# ============================================================

def main():

    print("=" * 60)
    print("Enterprise RAG - Document Ingestion")
    print("=" * 60)

    pdf_files = list(DOCUMENTS_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {DOCUMENTS_DIR}")
        return

    print(f"\nFound {len(pdf_files)} PDF file(s).")

    # --------------------------------------------------------
    # Load embedding model
    # --------------------------------------------------------

    print("\nLoading embedding model...")

    model = SentenceTransformer(EMBEDDING_MODEL)

    embedding_dimension = model.get_sentence_embedding_dimension()

    print(f"Embedding dimension: {embedding_dimension}")

    # --------------------------------------------------------
    # Connect to Qdrant
    # --------------------------------------------------------

    client = QdrantClient(url=QDRANT_URL)

    collections = [
        collection.name
        for collection in client.get_collections().collections
    ]

    if COLLECTION_NAME not in collections:

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=embedding_dimension,
                distance=Distance.COSINE,
            ),
        )

        print(f"Created collection: {COLLECTION_NAME}")

    else:
        print(f"Collection already exists: {COLLECTION_NAME}")

    # --------------------------------------------------------
    # Process PDFs
    # --------------------------------------------------------

    point_id = 0

    for pdf_path in pdf_files:

        print(f"\nProcessing: {pdf_path.name}")

        pages = extract_pdf_pages(pdf_path)

        print(f"Extracted {len(pages)} pages.")

        for page_data in pages:

            chunks = create_chunks(
                page_data["text"],
                CHUNK_SIZE,
                CHUNK_OVERLAP,
            )

            print(
                f"Page {page_data['page']}: "
                f"{len(chunks)} chunks"
            )

            for chunk in chunks:

                embedding = model.encode(
                    chunk,
                    normalize_embeddings=True,
                ).tolist()

                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "document": pdf_path.name,
                        "page": page_data["page"],
                    },
                )

                client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=[point],
                )

                point_id += 1

    print("\n" + "=" * 60)
    print("Ingestion completed successfully.")
    print(f"Total vectors inserted: {point_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()