# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes import router
from app.core.config import get_settings
from app.utils.vectorstore import get_embedder

settings = get_settings()


# ── 1. Lifespan FIRST (before FastAPI instantiation) ──────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("⏳ Loading embedding model...")
    get_embedder()                        # pre-warms the model cache
    print("✅ Embedding model ready.")
    yield
    # anything after yield runs on shutdown (cleanup if needed)


# ── 2. Single FastAPI instance with lifespan passed in ────────────
app = FastAPI(
    title="Resume ATS Intelligence Platform",
    description="Rule-based ATS scoring + LLM suggestions + FAISS RAG chat",
    version="1.0.0",
    lifespan=lifespan,                    # ← attached here, not separately
)


# ── 3. Middleware ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 4. Routes ─────────────────────────────────────────────────────
app.include_router(router, prefix="/api")


# ── 5. Root endpoints ─────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "Resume ATS Intelligence Platform",
        "status": "running",
        "llm_provider": "ollama (mistral)" if settings.use_ollama else "external API",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}