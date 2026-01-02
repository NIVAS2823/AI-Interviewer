"""
Prompt Template Service
Manages AI prompt templates for resume parsing
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PromptTemplateService:
    """
    Service for managing AI prompt templates
    
    Responsibilities:
    - Store prompt templates
    - Build prompts with context
    - Version control for prompts
    
    Does NOT:
    - Call LLM APIs
    - Parse responses
    - Extract data
    """

    # Resume parsing system prompt
    RESUME_PARSING_SYSTEM_PROMPT = """You are an advanced Applicant Tracking System (ATS) and expert resume parser 
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
{
  "name": "",
  "email": "",
  "phone": "",
  "linkedin": "",
  "github": "",
  "portfolio": "",
  "summary": "",
  "skills": {
     "keywords": [],
     "technical": [],
     "soft": [],
     "tools": [],
     "ats_top_matches": [],
     "keyword_density_score": 0
  },
  "experience": [
    {
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
    }
  ],
  "education": [
    {
      "institution": "",
      "degree": "",
      "field": "",
      "start_year": "",
      "end_year": "",
      "cgpa": ""
    }
  ],
  "projects": [
    {
      "title": "",
      "description": "",
      "technologies": [],
      "impact": ""
    }
  ],
  "certifications": [],
  "languages": [],
  "ats_scores": {
      "overall_score": 0,
      "skills_score": 0,
      "experience_score": 0,
      "education_score": 0,
      "projects_score": 0,
      "keyword_match_percentage": 0
  }
}

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

    # JSON schema for resume parsing
    RESUME_JSON_SCHEMA = {
        "name": "",
        "email": "",
        "phone": "",
        "linkedin": "",
        "github": "",
        "portfolio": "",
        "summary": "",
        "skills": {
            "keywords": [],
            "technical": [],
            "soft": [],
            "tools": [],
            "ats_top_matches": [],
            "keyword_density_score": 0
        },
        "experience": [
            {
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
            }
        ],
        "education": [
            {
                "institution": "",
                "degree": "",
                "field": "",
                "start_year": "",
                "end_year": "",
                "cgpa": ""
            }
        ],
        "projects": [
            {
                "title": "",
                "description": "",
                "technologies": [],
                "impact": ""
            }
        ],
        "certifications": [],
        "languages": [],
        "ats_scores": {
            "overall_score": 0,
            "skills_score": 0,
            "experience_score": 0,
            "education_score": 0,
            "projects_score": 0,
            "keyword_match_percentage": 0
        }
    }

    def __init__(self):
        """Initialize prompt template service"""
        logger.debug("Prompt template service initialized")

    def get_resume_parsing_prompt(self, resume_text: str, max_text_length: int = 8000) -> str:
        """
        Build resume parsing prompt
        
        Args:
            resume_text: Full resume text
            max_text_length: Maximum text length to include
            
        Returns:
            Complete prompt string
        """
        # Truncate text if too long
        truncated_text = resume_text[:max_text_length]
        if len(resume_text) > max_text_length:
            truncated_text += "\n... (truncated)"

        import json
        schema_str = json.dumps(self.RESUME_JSON_SCHEMA, indent=2)

        prompt = f"""
=========================
RESUME INPUT (partial):
{truncated_text}
=========================

Follow these INSTRUCTIONS exactly:

1. Output format:
   - Produce ONLY valid JSON matching the schema below.
   - Fields not present in the resume must be empty strings ("") or empty arrays ([]).
   - Maintain keys exactly as defined in the schema.
   - Output must be deterministic and parseable by automated systems.

2. Behavioral logic:
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
{schema_str}

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

        logger.debug(f"Built resume parsing prompt: {len(prompt)} chars")
        
        return prompt

    def get_system_prompt(self) -> str:
        """
        Get system prompt for resume parsing
        
        Returns:
            System prompt string
        """
        return self.RESUME_PARSING_SYSTEM_PROMPT

    def get_schema(self) -> Dict[str, Any]:
        """
        Get resume parsing JSON schema
        
        Returns:
            Schema dict
        """
        return self.RESUME_JSON_SCHEMA.copy()

    def get_schema_fields(self) -> list:
        """
        Get list of required schema fields
        
        Returns:
            List of field names
        """
        return list(self.RESUME_JSON_SCHEMA.keys())

    def validate_prompt_length(self, prompt: str, max_length: int = 12000) -> bool:
        """
        Validate prompt length
        
        Args:
            prompt: Prompt to validate
            max_length: Maximum allowed length
            
        Returns:
            True if valid
        """
        if len(prompt) > max_length:
            logger.warning(f"⚠️ Prompt too long: {len(prompt)} chars (max: {max_length})")
            return False
        
        return True

    def get_simplified_prompt(self, resume_text: str) -> str:
        """
        Get simplified prompt for faster parsing
        
        Args:
            resume_text: Resume text
            
        Returns:
            Simplified prompt
        """
        truncated_text = resume_text[:5000]

        return f"""Extract structured data from this resume in JSON format:

{truncated_text}

Return JSON with these fields:
- name, email, phone
- skills (array of strings)
- experience (array with company, role, duration)
- education (array with institution, degree, field)
- projects (array with title, description, technologies)

Output ONLY valid JSON, no markdown."""

    def get_template_version(self) -> str:
        """Get template version for tracking"""
        return "1.0.0"