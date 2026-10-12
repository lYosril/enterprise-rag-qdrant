
from app.worker import celery_app


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def index_document_task(self, document_id: str):
    # Implement the database lookup, PDF indexing,
    # status updates, and failure handling here.
    #
    # Load a fresh SQLAlchemy session inside the task.
    # Do not pass a live Session or ORM object to Celery.
    raise NotImplementedError(
        "Connect this task to your document service."
    )
