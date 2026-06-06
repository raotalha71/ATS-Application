

from app.core.llm_client import llm_complete
from app.agents.ats_engine import ATSReport


def build_suggestions_prompt(
    ats_report: ATSReport,
    candidate_name: str = "the candidate",
    job_description: str = "",
) -> str:
    """
    Builds a tight, focused prompt from ATS rule findings.
    Short prompt = faster Mistral generation.
    The model is told exactly what was found — it just explains it.
    """
    r = ats_report

    jd_context = job_description.strip() or "No job description was provided."

    prompt = f"""You are an expert resume coach. Based on the ATS analysis below, write 5-8 specific, actionable improvement suggestions for {candidate_name}'s resume.

RULES:
- Only suggest improvements based on the findings provided. Do NOT invent new rules.
- Be specific: name the exact problem and exact fix.
- Use plain language. No jargon.
- Each suggestion on a new line starting with a number.
- Treat the job description/position as the most important requirement.
- Compare the resume against the job description context below before giving advice.
- If the resume clearly fits a different role or industry, say "This candidate is not a fit for this role" as the first suggestion and explain the mismatch.
- Do not recommend hiring or shortlisting when the job-description keyword score is very low.

ATS FINDINGS:
- Job description context: {jd_context}
- Total Score: {r.total_score}/100 (Grade: {r.grade})
- Role Match: {r.role_match_score}/100 ({r.role_match_verdict})
- Missing sections: {r.sections_missing if r.sections_missing else 'None'}
- Weak verbs found: {r.weak_verbs_found[:8] if r.weak_verbs_found else 'None'}
- Missing keywords (vs job description): {r.missing_keywords[:10] if r.missing_keywords else 'None — no JD provided'}
- Quantified bullet points: {r.quantified_lines} out of {r.total_bullet_lines} total bullets
- Formatting warnings: {r.formatting_warnings if r.formatting_warnings else 'None'}
- Missing contact info: {[k for k,v in r.contact_findings.items() if not v]}
- Score breakdown: Contact={r.contact_score}/10, Sections={r.sections_score}/15, Verbs={r.action_verb_score}/15, Keywords={r.keyword_score}/25, Quantification={r.quantification_score}/20, Formatting={r.formatting_score}/15

Write the improvement suggestions now:"""

    return prompt


async def generate_suggestions(
    ats_report: ATSReport,
    candidate_name: str = "the candidate",
    job_description: str = "",
) -> str:
    """
    Calls LLM with ATS findings → returns suggestion text.
    """
    prompt = build_suggestions_prompt(ats_report, candidate_name, job_description)
    
    try:
        suggestions = await llm_complete(prompt)
        return suggestions.strip()
    except Exception as e:
        # If Ollama fails, return rule-based suggestions instead
        return f"""
Based on your ATS score of {ats_report.total_score}/100, here are key improvements:

1. Missing sections: {ats_report.sections_missing}
2. Weak verbs to replace: {ats_report.weak_verbs_found[:5]}
3. Missing keywords: {ats_report.missing_keywords[:10]}
4. Add quantification to {ats_report.total_bullet_lines - ats_report.quantified_lines} more bullet points
5. Contact info missing: {[k for k,v in ats_report.contact_findings.items() if not v]}

Note: LLM service unavailable. Using rule-based suggestions. Please restart Ollama.
"""
