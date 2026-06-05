
from dataclasses import dataclass, field
from typing import Optional
import faiss
import numpy as np


@dataclass
class ResumeRecord:
    """One record per uploaded resume."""
    resume_id: str
    filename: str
    raw_text: str                          # Full extracted text from PDF/DOCX
    job_description: str = ""             # JD used during ATS scoring, if provided
    document_validation: Optional[dict] = None  # Resume-vs-non-resume classifier output
    ats_report: Optional[dict] = None      # Set after ATS engine runs
    suggestions: Optional[str] = None      # Set after LLM suggestions agent runs
    faiss_index: Optional[faiss.IndexFlatL2] = None   # FAISS index for this resume
    chunks: list[str] = field(default_factory=list)   # Text chunks stored in FAISS
    chunk_metadata: list[dict] = field(default_factory=list)  # type: cv / ats / suggestions



RESUME_STORE: dict[str, ResumeRecord] = {}


def get_resume(resume_id: str) -> Optional[ResumeRecord]:
    return RESUME_STORE.get(resume_id)


def save_resume(record: ResumeRecord) -> None:
    RESUME_STORE[record.resume_id] = record


def list_resumes() -> list[dict]:
    return [
        {
            "resume_id": r.resume_id,
            "filename": r.filename,
            "ats_scored": r.ats_report is not None,
            "suggestions_ready": r.suggestions is not None,
            "faiss_ready": r.faiss_index is not None,
        }
        for r in RESUME_STORE.values()
    ]
