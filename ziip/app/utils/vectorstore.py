
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import get_settings

settings = get_settings()

# Load embedding model once at module level (cached in memory)
# all-MiniLM-L6-v2 → 384-dim, ~80MB, runs on CPU, ~20ms per embed
_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder



def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    """
    Split text into overlapping character-level chunks.
    Overlap ensures context isn't lost at chunk boundaries.
    """
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap  # slide forward with overlap

    # Remove empty chunks
    return [c for c in chunks if len(c) > 20]



def build_faiss_index(
    cv_text: str,
    ats_report_text: str,
    suggestions_text: str,
) -> tuple[faiss.IndexFlatL2, list[str], list[dict]]:
    """
    Builds a FAISS L2 index from 3 sources:
      1. CV raw text chunks       → metadata type: "cv"
      2. ATS report text chunks   → metadata type: "ats"
      3. Suggestions text chunks  → metadata type: "suggestions"

    Returns:
      - faiss_index: the built index
      - all_chunks: list of raw text for each vector
      - chunk_metadata: list of dicts with type info per chunk
    """
    embedder = get_embedder()
    all_chunks = []
    chunk_metadata = []

    # --- CV text chunks ---
    cv_chunks = chunk_text(cv_text)
    for c in cv_chunks:
        all_chunks.append(c)
        chunk_metadata.append({"type": "cv"})

    # --- ATS report chunks ---
    ats_chunks = chunk_text(ats_report_text)
    for c in ats_chunks:
        all_chunks.append(c)
        chunk_metadata.append({"type": "ats"})

    # --- Suggestions chunks ---
    sug_chunks = chunk_text(suggestions_text)
    for c in sug_chunks:
        all_chunks.append(c)
        chunk_metadata.append({"type": "suggestions"})

    if not all_chunks:
        raise ValueError("No text to index — all sources were empty.")

    # Embed all chunks in one batch (fast)
    embeddings = embedder.encode(all_chunks, show_progress_bar=False)
    embeddings = np.array(embeddings).astype("float32")

    # Build FAISS flat L2 index (exact search, fine for <200 chunks)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    return index, all_chunks, chunk_metadata



def retrieve_chunks(
    query: str,
    faiss_index: faiss.IndexFlatL2,
    all_chunks: list[str],
    chunk_metadata: list[dict],
    top_k: int = None,
    allowed_types: set[str] | None = None,
) -> list[dict]:
    """
    Embeds the query and retrieves top_k most relevant chunks.
    Returns list of { text, type, score } dicts.

    Keeping top_k=3 (default from settings) is critical for low latency —
    less context injected into Mistral = faster generation.
    """
    top_k = top_k or settings.faiss_top_k
    embedder = get_embedder()

    search_k = top_k if not allowed_types else max(top_k * 4, top_k)

    # Embed query
    query_vec = embedder.encode([query], show_progress_bar=False)
    query_vec = np.array(query_vec).astype("float32")

    # Search
    distances, indices = faiss_index.search(query_vec, search_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue  # FAISS returns -1 for empty slots
        chunk_type = chunk_metadata[idx]["type"]
        if allowed_types and chunk_type not in allowed_types:
            continue
        results.append({
            "text": all_chunks[idx],
            "type": chunk_type,
            "score": float(dist),   # L2 distance — lower = more relevant
        })

        if len(results) >= top_k:
            break

    return results


def format_context_for_prompt(retrieved_chunks: list[dict]) -> str:
    """
    Formats retrieved chunks into a clean context block for LLM prompt injection.
    Labels each chunk by its source type so LLM knows what it's reading.
    """
    sections = []
    for chunk in retrieved_chunks:
        label = {
            "cv": "📄 CV CONTENT",
            "ats": "📊 ATS ANALYSIS",
            "suggestions": "💡 IMPROVEMENT SUGGESTIONS",
        }.get(chunk["type"], "CONTEXT")
        sections.append(f"[{label}]\n{chunk['text']}")

    return "\n\n".join(sections)
