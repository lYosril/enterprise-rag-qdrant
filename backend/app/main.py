
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.routes import router
from app.db.session import SessionLocal, engine
from app.services.document_service import ensure_collection
from app.core.logging_config import configure_logging

configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.include_router(auth_router)

# Configure CORS for development and deployment origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
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


from prometheus_client import make_asgi_app

app.include_router(router)
app.mount("/metrics", make_asgi_app())
