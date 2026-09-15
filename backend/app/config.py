"""
Centralized configuration. Loads from environment variables / .env file.
Keeping all tunables here means the RAG pipeline, LLM client, and DB layer
never hardcode secrets or paths.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Storage
    chroma_persist_dir: str = "./chroma_db"
    sqlite_db_path: str = "./audit.db"

    # Auth
    admin_api_key: str = "change-me-admin-key"

    # Retrieval
    retrieval_top_k: int = 4
    embedding_model: str = "all-MiniLM-L6-v2"


settings = Settings()
