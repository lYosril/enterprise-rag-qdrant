
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    database_url: str
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "enterprise_documents"
    embedding_model: str = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    llm_api_key: str
    llm_base_url: str = (
        "https://api.groq.com/openai/v1"
    )
    llm_model: str

    cross_encoder_model: str = (
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    rag_dense_candidate_limit: int = 20
    rag_lexical_candidate_limit: int = 20
    rag_use_hybrid: bool = True
    rag_use_rerank: bool = True
    rrf_k: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

settings = Settings()