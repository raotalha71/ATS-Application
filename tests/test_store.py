from pathlib import Path

import faiss
import pytest

from app.core import store
from app.core.store import ResumeRecord, get_resume, list_resumes, save_resume


@pytest.fixture()
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "resumes.db")
    monkeypatch.setattr(store, "FAISS_DIR", tmp_path / "faiss")
    monkeypatch.setattr(store, "CHUNKS_DIR", tmp_path / "chunks")
    monkeypatch.setattr(store, "_STORAGE_READY", False)
    store.RESUME_STORE.clear()
    yield tmp_path
    store.RESUME_STORE.clear()
    monkeypatch.setattr(store, "_STORAGE_READY", False)


def test_save_resume_persists_sqlite_faiss_and_chunks(isolated_storage):
    index = faiss.IndexFlatL2(2)
    record = ResumeRecord(
        resume_id="resume-1",
        filename="resume.pdf",
        raw_text="Resume text",
        job_description="Python developer",
        document_validation={"is_resume": True, "confidence": 90},
        ats_report={"total_score": 80},
        suggestions="Improve keywords.",
        faiss_index=index,
        chunks=["Resume chunk", "ATS chunk"],
        chunk_metadata=[{"type": "cv"}, {"type": "ats"}],
    )

    save_resume(record)
    store.RESUME_STORE.clear()

    loaded = get_resume("resume-1")

    assert loaded is not None
    assert loaded.filename == "resume.pdf"
    assert loaded.document_validation["is_resume"] is True
    assert loaded.ats_report["total_score"] == 80
    assert loaded.chunks == ["Resume chunk", "ATS chunk"]
    assert loaded.chunk_metadata == [{"type": "cv"}, {"type": "ats"}]
    assert loaded.faiss_index is not None
    assert Path(isolated_storage / "resumes.db").exists()
    assert Path(isolated_storage / "faiss" / "resume-1.index").exists()
    assert Path(isolated_storage / "chunks" / "resume-1.json").exists()


def test_list_resumes_reads_from_sqlite(isolated_storage):
    save_resume(
        ResumeRecord(
            resume_id="resume-2",
            filename="resume.docx",
            raw_text="Resume text",
            ats_report={"total_score": 75},
            suggestions="Add metrics.",
        )
    )

    rows = list_resumes()

    assert rows[0]["resume_id"] == "resume-2"
    assert rows[0]["ats_scored"] is True
    assert rows[0]["suggestions_ready"] is True
