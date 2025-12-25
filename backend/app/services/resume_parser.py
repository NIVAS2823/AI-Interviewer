# app/services/resume_parser_service.py

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional

from groq import Groq

from app.core.config import settings
from app.utils.sanitizer import sanitize_llm_output
from app.utils.pdf_parser import PDFParser
from app.models.resume import ParsedData, WorkExperience, Education,Project,Skills

logger = logging.getLogger(__name__)

class ResumeParserService:
    """
    AI-powered resume parsing with:
      - Groq LLM extraction (robust w/ retries & timeouts)
      - Strict sanitization of LLM output
      - Graceful fallback to basic keyword parser
      - Safe conversion into Pydantic models
    """

    GROQ_TIMEOUT = 20
    GROQ_RETRIES = 2
    GROQ_BACKOFF_BASE = 1.0

    def __init__(self):
        if settings.GROQ_API_KEY:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info("✅ Groq client initialized")
        else:
            self.client = None
            logger.warning("⚠️ GROQ_API_KEY missing — fallback parser enabled")

        self.model_sequence = ["llama-3.3-70b-versatile"]

    # ---------------------------------------------------------
    # Public entrypoint
    # ---------------------------------------------------------
    async def parse_resume(self, file_path: str) -> ParsedData:
        raw_text = PDFParser.extract_text(file_path)

        if not raw_text or len(raw_text) < 50:
            logger.error("❌ Resume text extraction failed or too short")
            raise ValueError("Resume text could not be extracted.")

        basic_info = PDFParser.extract_basic_info(raw_text)

        if self.client:
            parsed = await self._parse_with_groq(raw_text, basic_info)
        else:
            parsed = self._parse_basic(raw_text, basic_info)

        parsed.raw_text = raw_text[:50_000]
        return parsed

    # ---------------------------------------------------------
    # Prompt Builder
    # ---------------------------------------------------------
    def _build_prompt(self, text: str) -> str:
        return f"""
You are an advanced Applicant Tracking System (ATS) and expert resume parser 
specialized in structured information extraction and scoring resumes for technical roles.

Your primary goal is to:
1. Parse the given resume text into structured, machine-readable JSON.
2. Produce reliable ATS-style scores based purely on resume evidence.

=========================
RESUME INPUT (partial):
{text[:8000]}
=========================

Follow these INSTRUCTIONS exactly:

1. Output format:
   - Produce ONLY valid JSON. No markdown, commentary, or explanations.
   - Fields not present in the resume must be empty strings ("") or empty arrays ([]).
   - Maintain keys exactly as defined in the schema below.
   - Output must be deterministic and parseable by automated systems.

2. Behavioral logic:
   - Never infer or guess details not explicitly supported by the resume text.
   - Consolidate information even if repeated in multiple sections (e.g., skills, projects).
   - Normalize company names, roles, and tools (e.g., "Python Developer" not "python dev").
   - Use consistent casing for all skill and tool names.
   - Keep all date formats as found in text or normalized to YYYY or MMM YYYY where possible.
   - Do not fabricate end dates or institutions if missing.

3. Scoring and field guidance:
   - "keyword_density_score": Measure frequency and relevance of skill keywords across resume sections.
   - "seniority_score": Infer from verbs (e.g., led, managed, mentored = senior; assisted, supported = junior) and duration.
   - "impact_score": Rate based on presence of quantifiable outcomes or ownership keywords.
   - "keyword_match_percentage": Proportion of recurring technical terms in skills and experience.
   - "overall_score": Weighted composite (skills 40%, experience 30%, education 15%, projects 15%), scaled 0–100.

=========================
EXPECTED JSON SCHEMA:
=========================
{{
  "name": "",
  "email": "",
  "phone": "",
  "linkedin": "",
  "github": "",
  "portfolio": "",
  "summary": "",
  "skills": {{
     "keywords": [],
     "technical": [],
     "soft": [],
     "tools": [],
     "ats_top_matches": [],
     "keyword_density_score": 0
  }},
  "experience": [
    {{
      "company": "",
      "role": "",
      "location": "",
      "duration": "",
      "start_date": "",
      "end_date": "",
      "achievements": [],
      "technologies": [],
      "seniority_score": 0,
      "impact_score": 0
    }}
  ],
  "education": [
    {{
      "institution": "",
      "degree": "",
      "field": "",
      "start_year": "",
      "end_year": "",
      "cgpa": ""
    }}
  ],
  "projects": [
    {{
      "title": "",
      "description": "",
      "technologies": [],
      "impact": ""
    }}
  ],
  "certifications": [],
  "languages": [],
  "ats_scores": {{
      "overall_score": 0,
      "skills_score": 0,
      "experience_score": 0,
      "education_score": 0,
      "projects_score": 0,
      "keyword_match_percentage": 0
  }}
}}

=========================
STRICT ENFORCEMENT:
=========================
- Output only JSON, without formatting artifacts.
- Do not wrap JSON in triple backticks or markdown.
- Do not include explanations, prose, or annotations.
- Stay within information found in resume; no educated guesses.
- Maintain schema order, completeness, and validity.

Return the final JSON object as your only output.
"""

    # ---------------------------------------------------------
    # Groq Parsing Logic
    # ---------------------------------------------------------
    async def _parse_with_groq(self, text: str, basic_info: Dict) -> ParsedData:
        prompt = self._build_prompt(text)
        last_err: Optional[Exception] = None

        for model in self.model_sequence:
            for attempt in range(1, self.GROQ_RETRIES + 2):
                try:
                    logger.info("🧠 Groq parsing model=%s attempt=%s", model, attempt)
                    response = await self._call_groq_async(model, prompt)

                    raw_json = self._extract_json(response)
                    if raw_json is None:
                        raise ValueError("Groq returned no valid JSON")

                    safe = sanitize_llm_output(raw_json)
                    parsed = self._convert_safe(safe, basic_info)

                    logger.info("✅ Groq resume parsing successful")
                    return parsed

                except Exception as e:
                    last_err = e
                    backoff = self.GROQ_BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        "⚠️ Attempt failed: %s. Retrying in %ss", e, backoff
                    )
                    await asyncio.sleep(backoff)

        logger.error("❌ All Groq attempts failed. Last error: %s", last_err)
        return self._parse_basic(text, basic_info)

    async def _call_groq_async(self, model: str, prompt: str):
        """Threaded blocking call wrapped in an asyncio timeout."""
        if not self.client:
            raise RuntimeError("Groq client missing")

        def blocking():
            return self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You output JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2500,
            )

        coro = asyncio.to_thread(blocking)
        return await asyncio.wait_for(coro, timeout=self.GROQ_TIMEOUT)

    # ---------------------------------------------------------
    # JSON Extraction Helpers
    # ---------------------------------------------------------
    def _extract_json(self, response) -> Optional[Dict]:
        try:
            content = response.choices[0].message.content.strip()
            content = re.sub(r"^``````$", "", content, flags=re.MULTILINE).strip()
        except Exception:
            logger.exception("Failed to extract model content")
            return None

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            logger.warning("❌ No JSON object found in response")
            return None

        snippet = match.group()
        cleaned = re.sub(r",\s*}", "}", snippet)
        cleaned = re.sub(r",\s*]", "]", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.exception("JSON decode failed even after cleanup")
            return None

    # ---------------------------------------------------------
    # Basic Fallback Parser
    # ---------------------------------------------------------
    def _parse_basic(self, text: str, basic_info: Dict) -> ParsedData:
        logger.info("🔄 Fallback basic parser used")

        name = text.split("\n")[0].strip() if text else None
        skills = self._extract_skills_basic(text)

        parsed = ParsedData(
            name=name or basic_info.get("name"),
            email=basic_info.get("email"),
            phone=basic_info.get("phone"),
            summary=None,
            skills=skills,
            experience=[],
            education=[],
            certifications=[],
            projects=[],
            languages=[]
        )

        parsed.completeness_score = self.calculate_completeness_score(parsed)
        return parsed

    def _extract_skills_basic(self, text: str) -> List[str]:
        keywords = [
            "Python", "FastAPI", "React", "JavaScript", "Java", "PostgreSQL", "MySQL",
            "TensorFlow", "Machine Learning", "AI", "OpenCV", "Git", "REST API", "Docker",
            "Kubernetes", "AWS", "Flask", "HTML", "CSS"
        ]
        lower = text.lower()
        return [k for k in keywords if k.lower() in lower][:20]

    # ---------------------------------------------------------
    # Safe Conversion → ParsedData
    # ---------------------------------------------------------
    def _convert_safe(self, data: Dict, basic_info: Dict) -> ParsedData:
        try:
            experience = []
            for e in data.get("experience", []):
                if isinstance(e, dict):
                    experience.append(
                        WorkExperience(
                            company=e.get("company", "") or "",
                            role=e.get("role", "") or "",
                            duration=e.get("duration", "") or "",
                            description=e.get("description", "") or "",
                            technologies=e.get("technologies", []) or [],
                        )
                    )

            education = []
            for e in data.get("education", []):
                if isinstance(e, dict):
                    education.append(
                        Education(
                            institution=e.get("institution", "") or "",
                            degree=e.get("degree", "") or "",
                            field=e.get("field", "") or "",
                            year=e.get("year", "") or "",
                            gpa=e.get("cgpa", "") or "",
                        )
                    )

            projects = []
            for p in data.get("projects", []):
                if isinstance(p, dict):
                    projects.append(
                        Project(
                            name=p.get("title") or p.get("name") or "",
                            description=p.get("description", "") or "",
                            technologies=p.get("technologies", []) or [],
                            url=p.get("url"),
                        )
                    )

            parsed = ParsedData(
                name=data.get("name") or basic_info.get("name"),
                email=data.get("email") or basic_info.get("email"),
                phone=data.get("phone") or basic_info.get("phone"),
                summary=data.get("summary") or "",
                skills = Skills(**data.get("skills", {})),
                experience=experience,
                education=education,
                certifications=data.get("certifications", []) or [],
                projects=projects,
                languages=data.get("languages", []) or [],
                raw_text=None,
            )

            parsed.completeness_score = self.calculate_completeness_score(parsed)
            return parsed

        except Exception as e:
            logger.exception("❌ Sanitized → ParsedData conversion failed: %s", e)
            return self._parse_basic(data.get("raw_text", ""), basic_info)

    # ---------------------------------------------------------
    # Scoring
    # ---------------------------------------------------------
    def calculate_completeness_score(self, parsed: ParsedData) -> int:
        score = 0

        # Basic identity info
        if parsed.name:
            score += 10
        if parsed.email:
            score += 8
        if parsed.phone:
            score += 7

        # Summary quality
        if parsed.summary and len(parsed.summary) > 50:
            score += 10

    # 🆕 Count skills properly (Skills is now an object, not a list)
        total_skills = (
            len(parsed.skills.keywords)
            + len(parsed.skills.technical)
            + len(parsed.skills.soft)
            + len(parsed.skills.tools)
        )

        # Skill scoring thresholds
        if total_skills >= 10:
            score += 20
        elif total_skills >= 5:
            score += 15
        elif total_skills > 0:
            score += 10

        # Experience scoring
        experience_count = len(parsed.experience)
        if experience_count >= 3:
            score += 25
        elif experience_count >= 2:
            score += 20
        elif experience_count >= 1:
            score += 15

        # Education
        if parsed.education:
            score += 10

        # Projects
        if parsed.projects:
            score += 5
        return min(score, 100)