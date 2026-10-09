
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()