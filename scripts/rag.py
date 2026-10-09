import os

import requests
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient


load_dotenv()


QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "enterprise_documents"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://api.groq.com/openai/v1",
)


def retrieve(query: str, top_k: int = 5):

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

    return results


def build_context(results):

    context_parts = []

    for result in results:

        document = result.payload["document"]
        page = result.payload["page"]
        text = result.payload["text"]

        context_parts.append(
            f"[Source: {document}, Page {page}]\n"
            f"{text}"
        )

    return "\n\n".join(context_parts)


def generate_answer(question: str, context: str):

    system_prompt = """
You are an enterprise knowledge assistant.

Answer the user's question using ONLY the provided context.

Rules:

1. Do not invent information.
2. Do not use outside knowledge.
3. If the context does not contain enough information,
   clearly say that the answer cannot be found in the
   provided documents.
4. Keep the answer concise and professional.
5. Mention the relevant source when possible.
"""

    user_prompt = f"""
Context:

{context}


Question:

{question}
"""

    response = requests.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "temperature": 0,
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]


def main():

    print("=" * 60)
    print("Enterprise RAG Assistant")
    print("=" * 60)

    question = input("\nAsk a question: ")

    print("\nSearching documents...")

    results = retrieve(question)

    context = build_context(results)

    print("\nGenerating answer...")

    answer = generate_answer(
        question,
        context,
    )

    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)

    print(answer)

    print("\n" + "=" * 60)
    print("SOURCES")
    print("=" * 60)

    seen = set()

    for result in results:

        document = result.payload["document"]
        page = result.payload["page"]

        source = (document, page)

        if source not in seen:

            print(
                f"- {document}, page {page}"
            )

            seen.add(source)


if __name__ == "__main__":
    main()