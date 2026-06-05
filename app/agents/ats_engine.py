
import re
from dataclasses import dataclass, field


STRONG_VERBS = {
    "engineered", "architected", "developed", "designed", "implemented",
    "optimized", "delivered", "launched", "led", "managed", "built",
    "created", "established", "transformed", "automated", "reduced",
    "increased", "improved", "streamlined", "spearheaded", "executed",
    "deployed", "integrated", "migrated", "scaled", "mentored", "drove",
    "achieved", "negotiated", "collaborated", "analyzed", "researched",
}

# Weak verbs that hurt ATS score
WEAK_VERBS = {
    "worked", "helped", "assisted", "participated", "was responsible",
    "involved", "did", "made", "handled", "used", "tried", "supported",
    "contributed to", "part of", "member of",
}

# Standard section headers ATS parsers look for
SECTION_HEADERS = {
    "experience": [
        "work experience", "experience", "employment history",
        "work history", "professional experience", "career history",
    ],
    "education": [
        "education", "academic background", "qualifications",
        "academic history", "degrees",
    ],
    "skills": [
        "skills", "core competencies", "technical skills",
        "key skills", "areas of expertise", "technologies",
    ],
    "summary": [
        "summary", "professional summary", "profile",
        "objective", "career objective", "about me",
    ],
    "contact": [
        "contact", "contact information", "personal details",
        "personal information",
    ],
}

# Common stop words for keyword extraction
STOP_WORDS = {
    "and", "the", "for", "with", "a", "an", "to", "in", "at", "of",
    "on", "is", "that", "from", "by", "or", "as", "it", "its", "are",
    "was", "were", "be", "been", "have", "has", "had", "do", "does",
    "will", "would", "could", "should", "may", "can", "this", "we",
    "our", "their", "they", "you", "your", "us", "me", "my",
}



class DocumentValidator:
    """
    Determines if uploaded text is actually a resume/CV.
    Returns confidence score 0-100.
    """
    
    RESUME_KEYWORDS = {
        "experience", "work", "employment", "education", "skills",
        "qualifications", "summary", "objective", "technical",
        "certifications", "projects", "achievements", "job title",
        "responsibilities", "bullet points"
    }
    
    def is_likely_resume(self, text: str) -> tuple[bool, float, str]:
        """
        Checks if text is likely a resume.
        Returns: (is_resume, confidence, reason)
        """
        text_lower = text.lower()
        
        # Count resume section headers
        section_count = 0
        found_sections = []
        
        sections = {
            "experience": ["work experience", "employment", "experience"],
            "education": ["education", "academic", "degree", "university"],
            "skills": ["skills", "technical", "competencies"],
            "summary": ["summary", "objective", "profile"]
        }
        
        for section_name, keywords in sections.items():
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text_lower) for kw in keywords):
                section_count += 1
                found_sections.append(section_name)
        
        # Check for name/contact info (resumes usually have this)
        has_email = bool(re.search(r'[\w.+-]+@[\w-]+\.\w+', text))
        has_phone = bool(re.search(r'(\+?\d[\d\s\-().]{7,15}\d)', text))
        
        # Scoring
        score = 0
        if section_count >= 3: score += 40      # Has 3+ standard sections
        if has_email: score += 20                 # Has email
        if has_phone: score += 15                 # Has phone
        if len(text) > 300: score += 10           # Reasonable length
        if "linkedin" in text_lower: score += 10  # LinkedIn mention
        if section_count == 0: score -= 50        # No CV sections = big red flag
        
        is_resume = score >= 50
        
        reason = f"Found {section_count} resume sections: {found_sections}. Email: {has_email}, Phone: {has_phone}. Score: {score}/100"
        
        return is_resume, min(score, 100), reason


@dataclass
class ATSReport:
    total_score: int = 0
    grade: str = ""

    # Category scores (out of max)
    contact_score: int = 0          # /10
    sections_score: int = 0         # /15
    action_verb_score: int = 0      # /15
    keyword_score: int = 0          # /25
    quantification_score: int = 0   # /20
    formatting_score: int = 0       # /15

    # Detailed findings
    contact_findings: dict = field(default_factory=dict)
    sections_found: dict = field(default_factory=dict)
    sections_missing: list = field(default_factory=list)
    strong_verbs_found: list = field(default_factory=list)
    weak_verbs_found: list = field(default_factory=list)
    matched_keywords: list = field(default_factory=list)
    missing_keywords: list = field(default_factory=list)
    keyword_match_pct: float = 0.0
    role_match_score: int = 0
    role_match_verdict: str = "No job description provided"
    quantified_lines: int = 0
    total_bullet_lines: int = 0
    formatting_warnings: list = field(default_factory=list)

    def to_text(self) -> str:
        """
        Converts report to plain text — used for FAISS chunking
        and as context for the LLM suggestions agent.
        """
        lines = [
            f"ATS SCORE REPORT",
            f"================",
            f"Total Score: {self.total_score}/100 (Grade: {self.grade})",
            f"",
            f"CATEGORY BREAKDOWN:",
            f"  Contact Info:      {self.contact_score}/10",
            f"  Sections Present:  {self.sections_score}/15",
            f"  Action Verbs:      {self.action_verb_score}/15",
            f"  Keyword Match:     {self.keyword_score}/25  ({self.keyword_match_pct:.1f}% match)",
            f"  Quantification:    {self.quantification_score}/20",
            f"  Formatting:        {self.formatting_score}/15",
            f"",
            f"ROLE ALIGNMENT: {self.role_match_score}/100 ({self.role_match_verdict})",
            f"JOB-DESCRIPTION KEYWORD MATCH: {self.keyword_match_pct:.1f}%",
            f"CONTACT FINDINGS: {self.contact_findings}",
            f"SECTIONS FOUND: {[k for k,v in self.sections_found.items() if v]}",
            f"SECTIONS MISSING: {self.sections_missing}",
            f"STRONG VERBS USED: {self.strong_verbs_found[:10]}",
            f"WEAK VERBS FOUND: {self.weak_verbs_found[:10]}",
            f"MATCHED KEYWORDS: {self.matched_keywords[:15]}",
            f"MISSING KEYWORDS: {self.missing_keywords[:15]}",
            f"QUANTIFIED LINES: {self.quantified_lines} of {self.total_bullet_lines}",
            f"FORMATTING WARNINGS: {self.formatting_warnings}",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "total_score": self.total_score,
            "grade": self.grade,
            "categories": {
                "contact_info": {"score": self.contact_score, "max": 10},
                "sections": {"score": self.sections_score, "max": 15},
                "action_verbs": {"score": self.action_verb_score, "max": 15},
                "keyword_match": {"score": self.keyword_score, "max": 25,
                                  "match_pct": self.keyword_match_pct},
                "role_match": {
                    "score": self.role_match_score,
                    "max": 100,
                    "verdict": self.role_match_verdict,
                },
                "quantification": {"score": self.quantification_score, "max": 20},
                "formatting": {"score": self.formatting_score, "max": 15},
            },
            "findings": {
                "contact": self.contact_findings,
                "sections_found": self.sections_found,
                "sections_missing": self.sections_missing,
                "strong_verbs": self.strong_verbs_found,
                "weak_verbs": self.weak_verbs_found,
                "matched_keywords": self.matched_keywords,
                "missing_keywords": self.missing_keywords,
                "quantified_lines": self.quantified_lines,
                "total_bullet_lines": self.total_bullet_lines,
                "formatting_warnings": self.formatting_warnings,
            },
        }


# ---------------------------------------------------------------
# ATS Engine
# ---------------------------------------------------------------

class ATSEngine:
    """
    Pure rule-based ATS scorer.
    Call .score(resume_text, job_description) to get ATSReport.
    job_description is optional — pass "" if not available.
    """

    # --- Category 1: Contact Info (10 pts) ---

    def _check_contact(self, text: str) -> tuple[int, dict]:
        """
        Checks for presence of email, phone, LinkedIn.
        Each item = partial score.
        """
        findings = {}
        score = 0

        # Email detection
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}', text)
        findings["email"] = bool(email_match)
        if email_match:
            score += 4

        # Phone detection (international + local formats)
        phone_match = re.search(
            r'(\+?\d[\d\s\-().]{7,15}\d)', text
        )
        findings["phone"] = bool(phone_match)
        if phone_match:
            score += 3

        # LinkedIn detection
        linkedin_match = re.search(
            r'linkedin\.com/in/[\w-]+', text, re.IGNORECASE
        )
        findings["linkedin"] = bool(linkedin_match)
        if linkedin_match:
            score += 3

        return min(score, 10), findings

    # --- Category 2: Mandatory Sections (15 pts) ---

    def _check_sections(self, text: str) -> tuple[int, dict, list]:
        """
        Scans for standard section headers using regex word boundaries.
        Returns score, found dict, and list of missing critical sections.
        """
        text_lower = text.lower()
        found = {}

        for section, keywords in SECTION_HEADERS.items():
            found[section] = any(
                re.search(r'\b' + re.escape(kw) + r'\b', text_lower)
                for kw in keywords
            )

        # Weighted section scoring
        # experience + skills are critical (5 pts each), others 2-3 pts
        score = 0
        if found.get("experience"):  score += 5
        if found.get("skills"):       score += 5
        if found.get("education"):    score += 3
        if found.get("summary"):      score += 1
        if found.get("contact"):      score += 1

        missing = [k for k, v in found.items() if not v and k in ("experience", "skills", "education")]

        return min(score, 15), found, missing

    # --- Category 3: Action Verb Strength (15 pts) ---

    def _check_action_verbs(self, text: str) -> tuple[int, list, list]:
        """
        Scans all words against strong/weak verb lists.
        Score = strong count bonus - weak count penalty, capped at 0-15.
        """
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())

        found_strong = list(set(w for w in words if w in STRONG_VERBS))
        found_weak = list(set(w for w in words if w in WEAK_VERBS))

        # +2 per unique strong verb (max 15), -1 per weak verb
        score = (len(found_strong) * 2) - (len(found_weak) * 1)
        score = max(0, min(score, 15))

        return score, found_strong, found_weak

    # --- Category 4: Keyword Match vs JD (25 pts) ---

    def _check_keywords(self, resume_text: str, job_description: str) -> tuple[int, list, list, float]:
        """
        Compares resume tokens against JD tokens.
        If no JD provided, scores 12/25 (neutral — can't evaluate without JD).
        """
        if not job_description.strip():
            # No JD — partial credit, neutral score
            return 12, [], [], 0.0

        def tokenize(t: str) -> set:
            words = re.findall(r'\b[a-zA-Z]{2,}\b', t.lower())
            return set(w for w in words if w not in STOP_WORDS)

        resume_tokens = tokenize(resume_text)
        jd_tokens = tokenize(job_description)

        matched = list(resume_tokens & jd_tokens)
        missing = list(jd_tokens - resume_tokens)
        pct = (len(matched) / len(jd_tokens) * 100) if jd_tokens else 0.0

        # Scale: 80%+ match = 25pts, linear below
        score = int((pct / 100) * 25)
        score = max(0, min(score, 25))

        return score, matched[:20], missing[:20], round(pct, 2)

    # --- Category 5: Quantification (20 pts) ---

    def _check_quantification(self, text: str) -> tuple[int, int, int]:
        """
        Counts bullet/achievement lines that contain numbers.
        "Increased sales by 40%" > "Increased sales"
        """
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Lines that look like bullet points or achievement statements
        bullet_lines = [
            l for l in lines
            if l.startswith(('-', '•', '*', '·', '–', '▪')) or
               (len(l) > 20 and l[0].isupper())
        ]

        # Lines with numbers/percentages (quantified)
        quantified = [
            l for l in bullet_lines
            if re.search(r'\d+', l)
        ]

        total = len(bullet_lines) if bullet_lines else 1
        ratio = len(quantified) / total

        # Score: 60%+ quantified = full 20 pts
        score = int(ratio * 20)
        score = max(0, min(score, 20))

        return score, len(quantified), len(bullet_lines)

    # --- Category 6: Formatting Cleanliness (15 pts) ---

    def _check_formatting(self, text: str) -> tuple[int, list]:
        """
        Flags ATS-unfriendly formatting patterns.
        Each flag deducts points from 15.
        """
        warnings = []
        deductions = 0

        # Multi-column indicators (large whitespace gaps or many tabs)
        if re.search(r'\s{6,}', text) or text.count('\t') > 8:
            warnings.append("Possible multi-column layout detected — ATS parsers may misread column order.")
            deductions += 4

        # Unsupported special characters / decorative bullets
        if re.search(r'[\u25A0-\u25FF\u2B00-\u2BFF\u2700-\u27BF]', text):
            warnings.append("Special bullet characters detected — may render as garbage in some ATS.")
            deductions += 3

        # Very long lines (no line breaks, wall of text)
        long_lines = [l for l in text.split('\n') if len(l) > 200]
        if long_lines:
            warnings.append(f"{len(long_lines)} very long line(s) found — consider breaking into bullets.")
            deductions += 2

        # Date format inconsistency
        date_formats = re.findall(
            r'\b(\d{1,2}/\d{4}|[A-Za-z]+ \d{4}|\d{4}-\d{2})\b', text
        )
        if len(set(date_formats)) > 2:
            warnings.append("Inconsistent date formats detected — standardize to 'Month YYYY'.")
            deductions += 2

        # Headers in ALL CAPS can confuse some parsers
        all_cap_headers = re.findall(r'\n[A-Z ]{4,}\n', text)
        if len(all_cap_headers) > 3:
            warnings.append("Many ALL-CAPS headers found — some ATS parsers skip these.")
            deductions += 2

        score = max(0, 15 - deductions)
        return score, warnings

    # --- Main Scorer ---

    def score(self, resume_text: str, job_description: str = "") -> ATSReport:
        """
        Run all 6 rule-based checks and compile ATSReport.
        Pure function — no LLM, no network, no side effects.
        """
        report = ATSReport()

        # Run all checks
        report.contact_score, report.contact_findings = self._check_contact(resume_text)
        report.sections_score, report.sections_found, report.sections_missing = self._check_sections(resume_text)
        report.action_verb_score, report.strong_verbs_found, report.weak_verbs_found = self._check_action_verbs(resume_text)
        report.keyword_score, report.matched_keywords, report.missing_keywords, report.keyword_match_pct = self._check_keywords(resume_text, job_description)
        report.role_match_score, report.role_match_verdict = self._role_match(report.keyword_match_pct, job_description)
        report.quantification_score, report.quantified_lines, report.total_bullet_lines = self._check_quantification(resume_text)
        report.formatting_score, report.formatting_warnings = self._check_formatting(resume_text)

        # Total
        report.total_score = (
            report.contact_score +
            report.sections_score +
            report.action_verb_score +
            report.keyword_score +
            report.quantification_score +
            report.formatting_score
        )

        # Grade
        report.grade = self._grade(report.total_score)

        return report

    def _role_match(self, keyword_match_pct: float, job_description: str) -> tuple[int, str]:
        """
        Separate job fit from resume quality.
        A polished resume can still be a poor match for the submitted job.
        """
        if not job_description.strip():
            return 0, "No job description provided"

        score = max(0, min(int(round(keyword_match_pct)), 100))
        if score >= 70:
            verdict = "Strong match - shortlist"
        elif score >= 45:
            verdict = "Partial match - manual review"
        else:
            verdict = "Poor match - do not shortlist"

        return score, verdict

    def _grade(self, score: int) -> str:
        if score >= 85: return "A — Excellent"
        if score >= 70: return "B — Good"
        if score >= 55: return "C — Average"
        if score >= 40: return "D — Below Average"
        return "F — Needs Major Rework"
