
import pytest
from app.agents.ats_engine import ATSEngine

engine = ATSEngine()

SAMPLE_RESUME = """
John Doe
john.doe@email.com | +1-555-123-4567 | linkedin.com/in/johndoe

PROFESSIONAL SUMMARY
Experienced software engineer with 5 years building scalable systems.

WORK EXPERIENCE
Software Engineer at TechCorp (Jan 2020 - Present)
- Engineered microservices using Python and Docker, reducing deployment time by 40%
- Architected REST APIs serving 10M requests/day
- Led a team of 4 engineers delivering 3 major product launches

EDUCATION
B.S. Computer Science, State University, 2019

SKILLS
Python, Java, Docker, Kubernetes, AWS, SQL, Git, React
"""

SAMPLE_JD = """
Looking for a Software Engineer proficient in Python, Docker, Kubernetes,
AWS, microservices architecture, and REST API design.
"""


def test_full_score():
    report = engine.score(SAMPLE_RESUME, SAMPLE_JD)
    assert report.total_score > 0
    assert report.total_score <= 100
    assert report.grade != ""


def test_contact_detection():
    report = engine.score(SAMPLE_RESUME)
    assert report.contact_findings["email"] is True
    assert report.contact_findings["phone"] is True
    assert report.contact_findings["linkedin"] is True
    assert report.contact_score == 10


def test_sections_detection():
    report = engine.score(SAMPLE_RESUME)
    assert report.sections_found["experience"] is True
    assert report.sections_found["education"] is True
    assert report.sections_found["skills"] is True


def test_action_verb_detection():
    report = engine.score(SAMPLE_RESUME)
    assert "engineered" in report.strong_verbs_found or "architected" in report.strong_verbs_found


def test_quantification():
    report = engine.score(SAMPLE_RESUME)
    assert report.quantified_lines > 0


def test_keyword_match():
    report = engine.score(SAMPLE_RESUME, SAMPLE_JD)
    assert report.keyword_match_pct > 0
    assert len(report.matched_keywords) > 0
    assert report.role_match_score == round(report.keyword_match_pct)
    assert report.role_match_verdict != ""


def test_no_jd_gives_neutral_score():
    report = engine.score(SAMPLE_RESUME, "")
    assert report.keyword_score == 12  # Neutral score when no JD


def test_ats_report_to_text():
    report = engine.score(SAMPLE_RESUME, SAMPLE_JD)
    text = report.to_text()
    assert "ATS SCORE REPORT" in text
    assert "Total Score" in text


def test_ats_report_to_dict():
    report = engine.score(SAMPLE_RESUME, SAMPLE_JD)
    d = report.to_dict()
    assert "total_score" in d
    assert "categories" in d
    assert "findings" in d
    assert "role_match" in d["categories"]
