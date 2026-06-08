from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Optional

import faiss

from app.core.config import get_settings


@dataclass
class ResumeRecord:
    """One record per uploaded resume."""
    resume_id: str
    filename: str
    raw_text: str
    job_description: str = ""
    document_validation: Optional[dict] = None
    ats_report: Optional[dict] = None
    suggestions: Optional[str] = None
    faiss_index: Optional[faiss.Index] = None
    chunks: list[str] = field(default_factory=list)
    chunk_metadata: list[dict] = field(default_factory=list)


settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = Path(settings.storage_dir)
if not STORAGE_DIR.is_absolute():
    STORAGE_DIR = PROJECT_ROOT / STORAGE_DIR

DB_PATH = STORAGE_DIR / "resumes.db"
FAISS_DIR = STORAGE_DIR / "faiss"
CHUNKS_DIR = STORAGE_DIR / "chunks"

RESUME_STORE: dict[str, ResumeRecord] = {}
_STORAGE_READY = False


def _init_storage() -> None:
    """Create local persistence folders and SQLite table once."""
    global _STORAGE_READY
    if _STORAGE_READY:
        return

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resumes (
                resume_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                job_description TEXT NOT NULL DEFAULT '',
                document_validation TEXT,
                ats_report TEXT,
                suggestions TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    _STORAGE_READY = True


def _json_dumps(value: Optional[dict]) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: Optional[str]) -> Optional[dict]:
    if not value:
        return None
    return json.loads(value)


def _faiss_path(resume_id: str) -> Path:
    return FAISS_DIR / f"{resume_id}.index"


def _chunks_path(resume_id: str) -> Path:
    return CHUNKS_DIR / f"{resume_id}.json"


def _save_faiss_index(record: ResumeRecord) -> None:
    if record.faiss_index is not None:
        faiss.write_index(record.faiss_index, str(_faiss_path(record.resume_id)))


def _load_faiss_index(resume_id: str) -> Optional[faiss.Index]:
    path = _faiss_path(resume_id)
    if not path.exists():
        return None
    return faiss.read_index(str(path))


def _save_chunks(record: ResumeRecord) -> None:
    payload = {
        "chunks": record.chunks,
        "chunk_metadata": record.chunk_metadata,
    }
    _chunks_path(record.resume_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_chunks(resume_id: str) -> tuple[list[str], list[dict]]:
    path = _chunks_path(resume_id)
    if not path.exists():
        return [], []

    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("chunks", []), payload.get("chunk_metadata", [])


def _row_to_record(row: sqlite3.Row) -> ResumeRecord:
    chunks, chunk_metadata = _load_chunks(row["resume_id"])
    return ResumeRecord(
        resume_id=row["resume_id"],
        filename=row["filename"],
        raw_text=row["raw_text"],
        job_description=row["job_description"] or "",
        document_validation=_json_loads(row["document_validation"]),
        ats_report=_json_loads(row["ats_report"]),
        suggestions=row["suggestions"],
        faiss_index=_load_faiss_index(row["resume_id"]),
        chunks=chunks,
        chunk_metadata=chunk_metadata,
    )


def get_resume(resume_id: str) -> Optional[ResumeRecord]:
    """
    Load a resume from the in-memory cache first, then SQLite/FAISS/JSON.
    This makes uploaded resumes survive backend restarts.
    """
    if resume_id in RESUME_STORE:
        return RESUME_STORE[resume_id]

    _init_storage()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM resumes WHERE resume_id = ?",
            (resume_id,),
        ).fetchone()

    if row is None:
        return None

    record = _row_to_record(row)
    RESUME_STORE[record.resume_id] = record
    return record


def save_resume(record: ResumeRecord) -> None:
    """
    Persist resume metadata in SQLite, vectors in FAISS, and chunk text in JSON.
    FAISS only stores vectors, so chunks and metadata must be saved separately.
    """
    _init_storage()
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute(
            "SELECT created_at FROM resumes WHERE resume_id = ?",
            (record.resume_id,),
        ).fetchone()
        created_at = existing[0] if existing else now

        conn.execute(
            """
            INSERT OR REPLACE INTO resumes (
                resume_id,
                filename,
                raw_text,
                job_description,
                document_validation,
                ats_report,
                suggestions,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.resume_id,
                record.filename,
                record.raw_text,
                record.job_description,
                _json_dumps(record.document_validation),
                _json_dumps(record.ats_report),
                record.suggestions,
                created_at,
                now,
            ),
        )
        conn.commit()

    _save_faiss_index(record)
    _save_chunks(record)
    RESUME_STORE[record.resume_id] = record


def list_resumes() -> list[dict]:
    _init_storage()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT resume_id, filename, ats_report, suggestions, updated_at
            FROM resumes
            ORDER BY updated_at DESC
            """
        ).fetchall()

    return [
        {
            "resume_id": row["resume_id"],
            "filename": row["filename"],
            "ats_scored": row["ats_report"] is not None,
            "suggestions_ready": row["suggestions"] is not None,
            "faiss_ready": _faiss_path(row["resume_id"]).exists(),
        }
        for row in rows
    ]
