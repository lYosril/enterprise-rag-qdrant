from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient


QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "enterprise_documents"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def search(query: str, top_k: int = 5):

    model = SentenceTransformer(EMBEDDING_MODEL)

    client = QdrantClient(url=QDRANT_URL)

    query_embedding = model.encode(
        query,
        normalize_embeddings=True,
    ).tolist()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=top_k,
    ).points

    print("\n" + "=" * 70)
    print(f"QUERY: {query}")
    print("=" * 70)

    for i, result in enumerate(results, start=1):

        print(f"\n--- Result {i} ---")

        print(f"Score: {result.score:.4f}")

        print(
            f"Document: "
            f"{result.payload['document']}"
        )

        print(
            f"Page: "
            f"{result.payload['page']}"
        )

        print(
            f"\n{result.payload['text']}"
        )


if __name__ == "__main__":

    question = input("\nAsk a question: ")

    search(question)