
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

import os

# Configure CORS for development and deployment origins
cors_origins_raw = os.getenv("CORS_ORIGINS") or os.getenv("cors_origins", "")
if cors_origins_raw:
    allowed_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost",
        "http://localhost:80",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
