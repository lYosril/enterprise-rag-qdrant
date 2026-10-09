
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import router
from app.core.config import settings
from app.db.session import Base, engine, SessionLocal
from app.models.models import Document, Conversation, Message
from app.services.document_service import ensure_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenient for the local learning prototype.
    # Use Alembic migrations in later production milestones.
    Base.metadata.create_all(bind=engine)
    ensure_collection()
    yield
    engine.dispose()


app = FastAPI(
    title="Enterprise RAG Assistant API",
    description=(
        "Document ingestion, semantic retrieval, "
        "and grounded AI question answering."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# Restrict these origins to your actual frontend in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "service": "enterprise-rag-assistant",
        "database": "connected",
    }


app.include_router(router)