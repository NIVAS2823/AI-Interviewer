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
from app.models.resume import ParsedData, WorkExperience, Education, Project

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
        """Generate a stable JSON-only prompt for Groq."""
        return f"""
You are an expert resume parser and HR analyst.
Extract structured information and return ONLY valid JSON.

Resume Text:
{text[:8000]}

Return strictly this JSON structure:
{{
  "name": "",
  "email": "",
  "phone": "",
  "summary": "",
  "skills": [],
  "experience": [
    {{
      "company": "",
      "role": "",
      "duration": "",
      "description": "",
      "technologies": []
    }}
  ],
  "education": [
    {{
      "institution": "",
      "degree": "",
      "field": "",
      "year": "",
      "cgpa": ""
    }}
  ],
  "projects": [
    {{
      "title": "",
      "description": "",
      "technologies": []
    }}
  ],
  "certifications": [],
  "languages": []
}}

Rules:
- NO markdown.
- NO comments.
- Replace missing fields with "" or [].
- Output JSON ONLY.
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
                    logger.info(f"🧠 Groq parsing model={model} attempt={attempt}")
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
                    logger.warning(f"⚠️ Attempt failed: {e}. Retrying in {backoff}s")
                    await asyncio.sleep(backoff)

        logger.error(f"❌ All Groq attempts failed. Last error: {last_err}")
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
            content = re.sub(r"^```(json)?|```$", "", content, flags=re.MULTILINE).strip()
        except Exception:
            logger.exception("Failed to extract model content")
            return None

        # Try direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Extract largest JSON-like block
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            logger.warning("❌ No JSON object found")
            return None

        snippet = match.group()

        # Clean common JSON issues
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
                skills=data.get("skills", []) or [],
                experience=experience,
                education=education,
                certifications=data.get("certifications", []) or [],
                projects=projects,
                languages=data.get("languages", []) or [],
                raw_text=None,
            )

            parsed.completeness_score = self.calculate_completeness_score(parsed)
            return parsed

        except Exception:
            logger.exception("❌ Sanitized → ParsedData conversion failed. Using fallback.")
            return self._parse_basic(data.get("raw_text", ""), basic_info)

    # ---------------------------------------------------------
    # Scoring
    # ---------------------------------------------------------
    def calculate_completeness_score(self, parsed: ParsedData) -> int:
        score = 0

        if parsed.name: score += 10
        if parsed.email: score += 8
        if parsed.phone: score += 7
        if parsed.summary and len(parsed.summary) > 50: score += 10

        if len(parsed.skills) >= 10: score += 20
        elif len(parsed.skills) >= 5: score += 15
        elif parsed.skills: score += 10

        if len(parsed.experience) >= 3: score += 25
        elif len(parsed.experience) >= 2: score += 20
        elif parsed.experience: score += 15

        if parsed.education: score += 10
        if parsed.projects: score += 5

        return min(score, 100)
