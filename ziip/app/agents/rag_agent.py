

from typing import AsyncGenerator, Literal
from app.core.llm_client import llm_stream
from app.core.store import get_resume, ResumeRecord

QuestionRoute = Literal["job_match", "ats", "improvements", "cv", "out_of_scope"]


def is_job_match_question(question: str) -> bool:
    """Detect questions asking whether the resume fits or matches a job description."""
    q = question.lower()
    keywords = [
        "match the job description",
        "matches the job description",
        "fit the job description",
        "fit this job",
        "does this cv match",
        "does this resume match",
        "job description",
        "jd",
        "good fit",
        "suitable for",
        "aligned with",
        "should we hire",
        "should i hire",
        "should hire",
        "hire this",
        "give this person the job",
        "give them the job",
        "give job",
        "given the job",
        "given job",
        "keep this person",
        "keep this candidate",
        "reject this candidate",
        "shortlist",
        "not relevant",
        "irrelevant",
        "for this role",
        "for the role",
        "job is for",
        "role is for",
        "position is for",
        "good for",
        "good even if",
    ]
    return any(keyword in q for keyword in keywords)


def classify_question(question: str) -> QuestionRoute:
    """Route resume-chat questions to the right evidence source."""
    q = question.lower()

    if is_job_match_question(question):
        return "job_match"

    improvement_terms = [
        "improve", "improvement", "suggestion", "suggest", "better reach",
        "change", "fix", "rewrite", "make it better", "optimize",
    ]
    if any(term in q for term in improvement_terms):
        return "improvements"

    ats_terms = [
        "ats", "score", "weak", "weakness", "not good", "bad", "keyword",
        "missing", "format", "formatting", "section", "why is this cv",
        "why this cv", "why is this resume", "why this resume",
    ]
    if any(term in q for term in ats_terms):
        return "ats"

    cv_terms = [
        "cv", "resume", "candidate", "person", "background", "experience",
        "skill", "education", "project", "certification", "contact",
        "summary", "profile", "work", "job title", "degree",
    ]
    if any(term in q for term in cv_terms):
        return "cv"

    return "out_of_scope"


def build_job_match_response(record: ResumeRecord) -> str:
    """Build a grounded answer for resume-vs-JD questions from ATS data."""
    validation = record.document_validation or {}
    if validation.get("is_resume") is False:
        confidence = validation.get("confidence", 0)
        reason = validation.get("reason", "")
        return (
            "This upload does not look like a CV/resume, so I can't make a meaningful job-description match from it. "
            f"Classifier confidence: {confidence}. {reason}"
        )

    if not record.job_description.strip():
        return (
            "I can't reliably compare this CV to a job description because no job description was provided at upload time. "
            "Paste the JD and re-upload, and I can score the match directly."
        )

    if not record.ats_report:
        return "ATS data is missing for this resume, so I can't compare it to the job description yet."

    ats = record.ats_report
    categories = ats.get("categories", {})
    findings = ats.get("findings", {})
    keyword_match = categories.get("keyword_match", {})
    role_match = categories.get("role_match", {})
    match_pct = float(keyword_match.get("match_pct", 0.0))
    role_score = int(role_match.get("score", round(match_pct)))
    role_verdict = role_match.get("verdict", "")
    total_score = int(ats.get("total_score", 0))
    grade = ats.get("grade", "")

    if role_score >= 70:
        decision = "Yes - shortlist this candidate."
        verdict = "strong role match"
        reason = "The CV shares enough required job-description keywords to justify moving forward."
    elif role_score >= 45:
        decision = "Maybe - review manually before shortlisting."
        verdict = "partial role match"
        reason = "There is some overlap, but important job requirements are still missing."
    else:
        decision = "No - do not shortlist this candidate for this role."
        verdict = "poor role match"
        reason = (
            "The CV does not show enough evidence for the provided job position. "
            "Relevant experience in another field should not be treated as suitable for this job."
        )

    matched_keywords = findings.get("matched_keywords", [])[:8]
    missing_keywords = findings.get("missing_keywords", [])[:8]
    missing_sections = findings.get("sections_missing", [])
    quant_total = findings.get("total_bullet_lines", 0)
    quant_done = findings.get("quantified_lines", 0)

    response_lines = [
        f"Hiring verdict: {decision}",
        f"Role alignment: {verdict}. {reason}",
        f"Resume quality score: {total_score}/100 ({grade}). Role match score: {role_score}/100.",
        f"Job-description keyword match: {match_pct:.1f}%.",
    ]

    if role_verdict:
        response_lines.append(f"Stored role verdict: {role_verdict}.")

    if matched_keywords:
        response_lines.append(f"Matched keywords: {', '.join(matched_keywords)}.")
    if missing_keywords:
        response_lines.append(f"Missing keywords: {', '.join(missing_keywords)}.")
    if missing_sections:
        response_lines.append(f"Missing sections: {', '.join(missing_sections)}.")
    if quant_total:
        response_lines.append(f"Quantification: {quant_done}/{quant_total} bullet lines include numbers.")

    response_lines.append("Decision rule: the job position/JD is the priority; a strong CV in a different field is still not a fit.")
    return " ".join(response_lines)


def build_rag_prompt(question: str, context: str, route: QuestionRoute) -> str:
    """
    Builds RAG prompt. Context is pre-formatted chunks from FAISS.
    System instruction keeps answers grounded — no hallucination.

    Key instruction: ONLY answer from provided context.
    If ATS/score info not in context → say so (don't guess).
    """
    return f"""[INST] You are a resume analysis assistant. Answer the user's question using ONLY the context provided below. The context contains excerpts from the resume (CV CONTENT), ATS analysis (ATS ANALYSIS), and improvement suggestions (IMPROVEMENT SUGGESTIONS).

STRICT RULES:
1. Only use information from the context. Do not add outside knowledge.
2. If the question is about ATS score, keywords, or weaknesses — answer from ATS ANALYSIS section.
3. If the question is about the person's background/skills/experience — answer from CV CONTENT section.
4. If the question is about improvements — answer from IMPROVEMENT SUGGESTIONS section.
5. If the context doesn't contain enough info to answer, say: "I don't have enough information in this resume's data to answer that."
6. Be concise and direct. No unnecessary filler.

QUESTION ROUTE: {route}

CONTEXT:
{context}

QUESTION: {question}

ANSWER: [/INST]"""


async def rag_chat_stream(
    resume_id: str,
    question: str,
) -> AsyncGenerator[str, None]:
    """
    Main RAG chat entry point.
    Retrieves FAISS chunks for this resume, builds prompt, streams LLM response.

    Yields string tokens as they're generated.
    Client receives them via Server-Sent Events (SSE).
    """
    # Load resume record
    record: ResumeRecord = get_resume(resume_id)

    if record is None:
        yield f"Resume ID '{resume_id}' not found. Please upload the resume first."
        return

    if record.faiss_index is None:
        yield "This resume hasn't been indexed yet. Please trigger the ATS scoring first."
        return

    validation = record.document_validation or {}
    if validation.get("is_resume") is False:
        confidence = validation.get("confidence", 0)
        reason = validation.get("reason", "")
        yield (
            "This upload does not look like a CV/resume, but I still processed it so the agent can inspect it. "
            f"Classifier confidence: {confidence}. {reason}"
        )
        return

    if is_job_match_question(question):
        yield build_job_match_response(record)
        return

    route = classify_question(question)
    if route == "out_of_scope":
        yield (
            "I can only answer questions about this uploaded CV, its ATS analysis, improvement suggestions, "
            "or its fit for the provided job description."
        )
        return

    from app.utils.vectorstore import retrieve_chunks, format_context_for_prompt

    allowed_types_by_route = {
        "ats": {"ats"},
        "improvements": {"suggestions", "ats"},
        "cv": {"cv"},
    }

    # Retrieve top-K relevant chunks from FAISS
    retrieved = retrieve_chunks(
        query=question,
        faiss_index=record.faiss_index,
        all_chunks=record.chunks,
        chunk_metadata=record.chunk_metadata,
        allowed_types=allowed_types_by_route.get(route, {"cv"}),
    )

    if not retrieved:
        yield "No relevant information found in this resume's index."
        return

    # Format chunks into context block
    context = format_context_for_prompt(retrieved)

    # Build RAG prompt
    prompt = build_rag_prompt(question, context, route)

    # Stream LLM response token by token
    async for token in llm_stream(prompt):
        yield token
