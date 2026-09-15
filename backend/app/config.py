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

    # Groq — free tier, no credit card (https://console.groq.com)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Google AI Studio / Gemini — free tier, no credit card (https://aistudio.google.com)
    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    # Storage
    chroma_persist_dir: str = "./chroma_db"
    sqlite_db_path: str = "./audit.db"

    # Auth
    admin_api_key: str = "change-me-admin-key"

    # Retrieval
    retrieval_top_k: int = 4
    embedding_model: str = "all-MiniLM-L6-v2"


settings = Settings()
