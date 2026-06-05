from app.agents.rag_agent import build_job_match_response, is_job_match_question
from app.core.store import ResumeRecord


def test_match_question_detection():
    assert is_job_match_question("Does this CV match the job description?") is True
    assert is_job_match_question("Should this person be given the job?") is True
    assert is_job_match_question("Should we hire this candidate for the role?") is True
    assert is_job_match_question("What skills does this person have?") is False


def test_job_match_response_uses_ats_data():
    record = ResumeRecord(
        resume_id="1",
        filename="resume.pdf",
        raw_text="sample resume",
        job_description="Looking for Python and AWS experience",
        ats_report={
            "total_score": 72,
            "grade": "B — Good",
            "categories": {
                "keyword_match": {"match_pct": 60.0},
            },
            "findings": {
                "matched_keywords": ["python", "aws"],
                "missing_keywords": ["kubernetes"],
                "sections_missing": ["education"],
                "quantified_lines": 3,
                "total_bullet_lines": 5,
            },
        },
    )

    response = build_job_match_response(record)

    assert "Maybe - review manually before shortlisting" in response
    assert "partial role match" in response
    assert "Job-description keyword match: 60.0%" in response
    assert "Matched keywords: python, aws" in response
    assert "Missing sections: education" in response


def test_job_match_response_rejects_low_role_alignment():
    record = ResumeRecord(
        resume_id="1",
        filename="ai-resume.pdf",
        raw_text="AI ML engineer resume",
        job_description="Fashion designer role requiring garment construction, pattern making, textiles, and trend forecasting",
        ats_report={
            "total_score": 38,
            "grade": "F - Needs Major Rework",
            "categories": {
                "keyword_match": {"match_pct": 8.0},
            },
            "findings": {
                "matched_keywords": ["designer"],
                "missing_keywords": ["fashion", "garment", "pattern", "textiles"],
                "sections_missing": [],
                "quantified_lines": 1,
                "total_bullet_lines": 4,
            },
        },
    )

    response = build_job_match_response(record)

    assert "No - do not shortlist this candidate for this role" in response
    assert "poor role match" in response
    assert "strong CV in a different field is still not a fit" in response


def test_job_match_response_handles_missing_jd():
    record = ResumeRecord(
        resume_id="1",
        filename="resume.pdf",
        raw_text="sample resume",
        job_description="",
        ats_report={
            "total_score": 72,
            "grade": "B — Good",
            "categories": {},
            "findings": {},
        },
    )

    response = build_job_match_response(record)

    assert "can't reliably compare" in response
