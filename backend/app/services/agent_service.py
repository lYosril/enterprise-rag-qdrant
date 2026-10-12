
from app.services.rag_service import answer_question


MAX_RETRIEVAL_ATTEMPTS = 2


def answer_with_agent(question: str, owner_id: str) -> dict:
    """
    Controlled agentic RAG:
    - Retrieve evidence.
    - Check whether useful sources were found.
    - Optionally retry with a refined query.
    - Return a grounded answer with trace metadata.
    """

    attempts = []
    current_question = question

    for attempt in range(MAX_RETRIEVAL_ATTEMPTS):
        result = answer_question(
            current_question,
            owner_id=owner_id,
        )

        sources = result.get("sources", [])

        attempts.append({
            "attempt": attempt + 1,
            "query": current_question,
            "source_count": len(sources),
        })

        if sources:
            return {
                **result,
                "agent_trace": attempts,
            }

        # A real query-rewriting function should be added here.
        # Avoid repeating the identical query without a change.
        break

    return {
        "answer": (
            "I couldn't find sufficient evidence in your "
            "authorized documents to answer that question."
        ),
        "sources": [],
        "agent_trace": attempts,
    }
