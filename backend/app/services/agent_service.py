"""
Agent Service: controlled, bounded agentic RAG with query rewriting,
multi-document synthesis support, strict execution limits, and safe observability.
"""

import time
import uuid
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import (
    AGENT_REQUESTS_TOTAL,
    AGENT_RETRIEVAL_ATTEMPTS,
    log_agent_turn,
    logger,
)
from app.db.session import SessionLocal
from app.services.query_rewriter import (
    has_reference_tokens,
    is_retrieval_weak,
    rewrite_query,
)
from app.services.rag_service import answer_question
from app.services.reranker import rerank_chunks
from app.services.retrieval_service import retrieve_ranked_chunks


def answer_with_agent(
    question: str,
    owner_id: str,
    db: Session | None = None,
    history: list[dict] | None = None,
) -> dict:
    """
    Controlled agentic RAG execution:
    1. Enforces strict limits (at most 2 retrieval attempts, 20 candidates/attempt, top 5 context).
    2. Uses conversation history to resolve vague/coreferential queries before or during retrieval.
    3. Retries with query rewriting only when the first retrieval is measurably weak.
    4. Groups and synthesizes evidence across multiple documents.
    5. Abstains cleanly when evidence is insufficient.
    6. Logs query identifier, retrieval attempts, latency, token usage without leaking content.
    """
    start_time = time.perf_counter()
    query_id = str(uuid.uuid4())
    history = history or []
    attempts_trace = []
    close_db = False

    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Step 1: Query preparation - if history exists and question has coreference tokens,
        # resolve references before initial retrieval.
        search_query_1 = question
        initial_rewrite_done = False
        if history and has_reference_tokens(question):
            rewrite_res = rewrite_query(
                question,
                history,
                max_history_turns=settings.agent_max_history_turns,
            )
            if rewrite_res.was_rewritten:
                search_query_1 = rewrite_res.query
                initial_rewrite_done = True

        # Attempt 1: Read-only candidate retrieval (capped at settings.agent_retrieved_candidates_limit)
        sources_1 = retrieve_ranked_chunks(
            search_query_1,
            owner_id,
            db,
            use_hybrid=settings.rag_use_hybrid,
            use_rerank=settings.rag_use_rerank,
            final_top_k=settings.agent_final_top_k,
        )

        attempts_trace.append({
            "attempt": 1,
            "query": search_query_1,
            "was_rewritten": initial_rewrite_done,
            "source_count": len(sources_1),
            "source_ids": [s["chunk_id"] for s in sources_1],
        })

        best_sources = sources_1

        # Step 2: Measure if retrieval is weak to decide whether a second retrieval attempt is justified
        weak = is_retrieval_weak(
            sources_1,
            threshold=settings.agent_weak_retrieval_threshold,
        )

        # Step 3: Attempt 2 (Strictly bounded: at most 2 retrieval attempts)
        if weak and settings.agent_max_retrieval_attempts >= 2:
            search_query_2 = None
            if not initial_rewrite_done and history:
                # Rewrite using conversation history
                rewrite_res_2 = rewrite_query(
                    question,
                    history,
                    max_history_turns=settings.agent_max_history_turns,
                )
                if rewrite_res_2.was_rewritten and rewrite_res_2.query != search_query_1:
                    search_query_2 = rewrite_res_2.query

            # If no history rewrite occurred or query was unchanged, try fallback search query
            if not search_query_2 and question != search_query_1:
                search_query_2 = question

            if search_query_2 and search_query_2 != search_query_1:
                logger.info(
                    "Weak retrieval (sources=%d). Retrying with rewritten query %r",
                    len(sources_1),
                    search_query_2[:80],
                )
                sources_2 = retrieve_ranked_chunks(
                    search_query_2,
                    owner_id,
                    db,
                    use_hybrid=settings.rag_use_hybrid,
                    use_rerank=settings.rag_use_rerank,
                    final_top_k=settings.agent_final_top_k,
                )

                attempts_trace.append({
                    "attempt": 2,
                    "query": search_query_2,
                    "was_rewritten": True,
                    "source_count": len(sources_2),
                    "source_ids": [s["chunk_id"] for s in sources_2],
                })

                # Merge candidates and keep top reranked chunks up to context budget
                combined = {s["chunk_id"]: s for s in (sources_1 + sources_2)}
                if settings.rag_use_rerank and combined:
                    reranked = rerank_chunks(
                        question,
                        list(combined.values()),
                        top_k=settings.agent_final_top_k,
                    )
                    best_sources = reranked
                else:
                    best_sources = list(combined.values())[:settings.agent_final_top_k]

        # Step 4: Missing evidence check -> Abstain
        if not best_sources:
            latency = time.perf_counter() - start_time
            outcome = "abstain"
            AGENT_RETRIEVAL_ATTEMPTS.observe(len(attempts_trace))
            AGENT_REQUESTS_TOTAL.labels(status="success", outcome=outcome).inc()
            log_agent_turn(
                query_id=query_id,
                attempt_count=len(attempts_trace),
                selected_source_ids=[],
                latency_seconds=latency,
                outcome=outcome,
            )
            return {
                "query_id": query_id,
                "answer": (
                    "I couldn't find sufficient evidence in your authorized documents "
                    "to answer that question."
                ),
                "sources": [],
                "agent_trace": attempts_trace,
            }

        # Step 5: Multi-document synthesis & answer generation
        synthesis_result = answer_question(
            question=question,
            owner_id=owner_id,
            db=db,
            custom_sources=best_sources,
        )

        latency = time.perf_counter() - start_time
        unique_docs = len({s.get("document") for s in best_sources})
        outcome = "multi_doc_synthesized" if unique_docs > 1 else "answered"

        AGENT_RETRIEVAL_ATTEMPTS.observe(len(attempts_trace))
        AGENT_REQUESTS_TOTAL.labels(status="success", outcome=outcome).inc()

        log_agent_turn(
            query_id=query_id,
            attempt_count=len(attempts_trace),
            selected_source_ids=[s["chunk_id"] for s in best_sources],
            latency_seconds=latency,
            outcome=outcome,
            token_usage=synthesis_result.get("token_usage"),
        )

        return {
            "query_id": query_id,
            "answer": synthesis_result["answer"],
            "sources": synthesis_result["sources"],
            "agent_trace": attempts_trace,
            "token_usage": synthesis_result.get("token_usage"),
        }

    finally:
        if close_db:
            db.close()
