"""
Celery asynchronous background tasks for document processing.
"""

from pathlib import Path
from app.core.logging_config import logger
from app.db.session import SessionLocal
from app.models.models import Document
from app.services.document_service import index_document
from app.worker import celery_app


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def index_document_task(self, document_id: str):
    """
    Asynchronous task to process and index an uploaded document.
    Loads a fresh SQLAlchemy session inside the worker process.
    """
    logger.info("celery_indexing_task_started", document_id=document_id)
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        if not doc:
            logger.error("celery_document_not_found", document_id=document_id)
            return {"status": "error", "message": "Document not found"}

        try:
            points_indexed = index_document(db, doc, Path(doc.stored_path))
            logger.info(
                "celery_indexing_task_completed",
                document_id=document_id,
                chunk_count=points_indexed,
            )
            return {
                "document_id": document_id,
                "chunk_count": points_indexed,
                "status": "indexed",
            }
        except Exception as exc:
            logger.exception(
                "celery_indexing_task_failed",
                document_id=document_id,
                error=str(exc),
            )
            raise
