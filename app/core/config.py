
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # LLM provider: "ollama", "openai", or "anthropic".
    # USE_OLLAMA is kept for older .env files; LLM_PROVIDER takes priority.
    llm_provider: str = ""
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

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    @property
    def active_llm_provider(self) -> str:
        """Return the configured provider while preserving USE_OLLAMA compatibility."""
        provider = (self.llm_provider or "").strip().lower()
        if provider:
            return provider
        return "ollama" if self.use_ollama else "openai"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings — only parsed once per process lifetime."""
    return Settings()
