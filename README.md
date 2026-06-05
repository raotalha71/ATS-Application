# ATS-Application

Resume ATS Intelligence Platform.

A FastAPI-based resume analysis system with rule-based ATS scoring, LLM suggestions, and FAISS-powered RAG chat.

## Stack

- **FastAPI** — REST API
- **FAISS** — In-memory vector store per resume
- **Mistral 7B via Ollama** — LLM for suggestions and RAG chat
- **PyMuPDF** — PDF text extraction
- **sentence-transformers** — Embeddings for FAISS
- **uv** — Package management

## Setup

```bash
# Install uv
curl -Lsf https://astral.sh/uv/install.sh | sh

# Create venv and install deps
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Copy and configure env
cp .env.example .env
# Edit .env — set USE_OLLAMA=true for local Mistral, or add API key

# Run Ollama in a separate terminal
ollama run mistral

# Start server
uvicorn app.main:app --reload --port 8000
```

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/upload` | Upload resume PDF/DOCX |
| GET | `/api/ats/{resume_id}` | Get ATS score report |
| GET | `/api/suggestions/{resume_id}` | Get LLM improvement suggestions |
| POST | `/api/chat/{resume_id}` | RAG chat (streamed) |
| GET | `/api/resumes` | List all uploaded resumes |

## Architecture

```mermaid
flowchart LR
    A[Upload] --> B[Extract Text]
    B --> C[Rule-Based ATS]
    C --> D[LLM Suggestions]
    D --> E[FAISS Index]
    E --> F[RAG Chat]
```
=======
# ATS-Application
>>>>>>> ddb99d311231fe091fca7470de5b10c3d7baab8c
