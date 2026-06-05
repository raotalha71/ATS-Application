
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM provider toggle
    use_ollama: bool = True

    # Ollama (local Mistral 7B)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    # Anthropic — uncomment ANTHROPIC_API_KEY in .env to activate
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"

    # OpenAI — uncomment OPENAI_API_KEY in .env to activate
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    max_upload_size_mb: int = 10

    # FAISS / chunking
    faiss_top_k: int = 3
    chunk_size: int = 400
    chunk_overlap: int = 50

    # Embedding model (local, no key needed)
    embedding_model: str = "all-MiniLM-L6-v2"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings — only parsed once per process lifetime."""
    return Settings()
