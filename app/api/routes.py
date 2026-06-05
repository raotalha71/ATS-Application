
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from app.core.store import ResumeRecord, save_resume, get_resume, list_resumes
from app.utils.extractor import extract_text
from app.agents.ats_engine import ATSEngine, DocumentValidator
from app.agents.suggestions_agent import generate_suggestions
from app.agents.rag_agent import rag_chat_stream
from app.utils.vectorstore import build_faiss_index
from app.core.config import get_settings
from pydantic import BaseModel

router = APIRouter()
settings = get_settings()
ats_engine = ATSEngine()  # Instantiate once — stateless, safe to share


# ---------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str


# ---------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = Form(default=""),
    candidate_name: str = Form(default="the candidate"),
):
    """
    Full pipeline:
    1. Extract text
    2. Classify whether it looks like a resume
    3. Score, index, and let agents surface the result later
    """
    # Extract text
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        raise HTTPException(413, f"File too large. Max {settings.max_upload_size_mb}MB.")

    try:
        raw_text = extract_text(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if len(raw_text.strip()) < 50:
        raise HTTPException(400, "Could not extract meaningful text from file.")

    validator = DocumentValidator()
    is_resume, confidence, reason = validator.is_likely_resume(raw_text)

    ats_report = ats_engine.score(raw_text, job_description)
    suggestions_text = await generate_suggestions(ats_report, candidate_name, job_description)
    faiss_index, all_chunks, chunk_metadata = build_faiss_index(
        cv_text=raw_text,
        ats_report_text=ats_report.to_text(),
        suggestions_text=suggestions_text,
    )

    resume_id = str(uuid.uuid4())
    record = ResumeRecord(
        resume_id=resume_id,
        filename=file.filename,
        raw_text=raw_text,
        job_description=job_description,
        document_validation={
            "is_resume": is_resume,
            "confidence": confidence,
            "reason": reason,
        },
        ats_report=ats_report.to_dict(),
        suggestions=suggestions_text,
        faiss_index=faiss_index,
        chunks=all_chunks,
        chunk_metadata=chunk_metadata,
    )
    save_resume(record)

    return {
        "resume_id": resume_id,
        "filename": file.filename,
        "candidate_name": candidate_name,
        "ats_score": ats_report.total_score,
        "grade": ats_report.grade,
        "sections_missing": ats_report.sections_missing,
        "validation": {
            "is_resume": is_resume,
            "confidence": confidence,
            "reason": reason,
        },
        "total_chunks_indexed": len(all_chunks),
    }

# ---------------------------------------------------------------
# GET /ats/{resume_id}
# ---------------------------------------------------------------

@router.get("/ats/{resume_id}")
async def get_ats_report(resume_id: str):
    """
    Returns the full ATS score report for a resume.
    No LLM call — purely rule-based data stored at upload time.
    """
    record = get_resume(resume_id)
    if not record:
        raise HTTPException(404, f"Resume '{resume_id}' not found.")
    if not record.ats_report:
        raise HTTPException(404, "ATS report not generated yet.")

    return {
        "resume_id": resume_id,
        "filename": record.filename,
        "ats_report": record.ats_report,
    }


# ---------------------------------------------------------------
# GET /suggestions/{resume_id}
# ---------------------------------------------------------------

@router.get("/suggestions/{resume_id}")
async def get_suggestions(resume_id: str):
    """
    Returns the pre-generated LLM improvement suggestions.
    Generated once at upload time — instant retrieval here.
    """
    record = get_resume(resume_id)
    if not record:
        raise HTTPException(404, f"Resume '{resume_id}' not found.")
    if not record.suggestions:
        raise HTTPException(404, "Suggestions not generated yet.")

    return {
        "resume_id": resume_id,
        "filename": record.filename,
        "suggestions": record.suggestions,
    }


# ---------------------------------------------------------------
# POST /chat/{resume_id}   — Streamed SSE
# ---------------------------------------------------------------

@router.post("/chat/{resume_id}")
async def chat_with_resume(resume_id: str, body: ChatRequest):
    """
    RAG chat endpoint — streams LLM response via Server-Sent Events.

    Client receives text tokens as they generate.
    This makes Mistral 7B feel fast despite 15s full latency:
    first token arrives in ~2-3s, rest streams progressively.

    Example curl:
      curl -N -X POST http://localhost:8000/api/chat/{resume_id} \\
        -H "Content-Type: application/json" \\
        -d '{"question": "Why is this CV weak?"}'
    """
    record = get_resume(resume_id)
    if not record:
        raise HTTPException(404, f"Resume '{resume_id}' not found.")

    async def event_stream():
        async for token in rag_chat_stream(resume_id, body.question):
            # SSE format: "data: <token>\n\n"
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable nginx buffering if behind proxy
        }
    )


# ---------------------------------------------------------------
# GET /resumes
# ---------------------------------------------------------------

@router.get("/resumes")
async def get_all_resumes():
    """Lists all uploaded resumes with their processing status."""
    return {"resumes": list_resumes()}
