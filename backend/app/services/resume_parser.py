"""
Resume Parser Service (Refactored)
Thin coordinator for resume parsing operations

Now delegates to specialized services:
- GroqService: LLM API calls
- PromptTemplateService: Prompt management
- BasicResumeParser: Fallback parsing
- ResumeDataMapper: JSON → Pydantic conversion
- ResumeQualityService: Quality scoring
"""
import logging

from app.core.config import settings
from app.utils.sanitizer import sanitize_llm_output
from app.utils.pdf_parser import PDFParser
from app.models.resume import ParsedData
from app.services.integration.groq_service import GroqService
from app.services.resume_parsing.prompt_template_service import PromptTemplateService
from app.services.resume_parsing.basic_resume_parser import BasicResumeParser
from app.services.resume_parsing.resume_quality_service import ResumeQualityService
from app.services.resume_parsing.resume_data_mapper import ResumeDataMapper

logger = logging.getLogger(__name__)


class ResumeParserService:
    """
    Resume Parser Service - Thin Coordinator
    
    Responsibilities (ONLY):
    - Coordinate parsing flow
    - Delegate to specialized services
    - Handle errors gracefully
    
    Does NOT:
    - Call LLM APIs directly (GroqService)
    - Build prompts (PromptTemplateService)
    - Extract JSON (GroqService + sanitizer)
    - Map data (ResumeDataMapper)
    - Calculate scores (ResumeQualityService)
    - Parse fallback (BasicResumeParser)
    """

    def __init__(self):
        """Initialize resume parser with all required services"""
        # Core services
        self.groq = GroqService()
        self.prompt_templates = PromptTemplateService()
        self.basic_parser = BasicResumeParser()
        self.quality_service = ResumeQualityService()
        self.data_mapper = ResumeDataMapper()

        if self.groq.is_available():
            logger.info("✅ Resume parser initialized (AI-powered)")
        else:
            logger.warning("⚠️ Resume parser initialized (fallback mode only)")

    async def parse_resume(self, file_path: str) -> ParsedData:
        """
        Parse resume from file
        
        Args:
            file_path: Path to resume PDF
            
        Returns:
            ParsedData instance
            
        Raises:
            ValueError: If text extraction fails
        """
        # Extract text from PDF
        raw_text = PDFParser.extract_text(file_path)

        if not raw_text or len(raw_text) < 50:
            logger.error("❌ Resume text extraction failed or too short")
            raise ValueError("Resume text could not be extracted.")

        # Extract basic info
        basic_info = PDFParser.extract_basic_info(raw_text)

        # Try AI parsing first
        if self.groq.is_available():
            parsed = await self._parse_with_ai(raw_text, basic_info)
        else:
            # Fallback to basic parser
            parsed = self.basic_parser.parse(raw_text, basic_info)

        # Add raw text (truncated)
        parsed.raw_text = raw_text[:50_000]

        logger.debug(f"Quality service methods: {dir(self.quality_service)}")
        
        logger.info("📊 Calculating resume completeness score")


        # Calculate quality score
        parsed.completeness_score = self.quality_service.calculate_completeness_score(parsed)

        logger.info(
            f"✅ Resume parsed: {parsed.name or 'Unknown'}, "
            f"Score: {parsed.completeness_score}/100"
        )

        return parsed

    async def _parse_with_ai(self, text: str, basic_info: dict) -> ParsedData:
        """
        Parse resume using AI (Groq LLM)
        
        Args:
            text: Resume text
            basic_info: Basic info from PDF
            
        Returns:
            ParsedData instance
        """
        logger.info("🧠 Parsing resume with AI")

        try:
            # Build prompt
            prompt = self.prompt_templates.get_resume_parsing_prompt(text)

            # Get system prompt
            system_prompt = self.prompt_templates.get_system_prompt()

            # Get expected fields
            expected_fields = self.prompt_templates.get_schema_fields()

            # Call Groq with retry (handled by GroqService)
            json_data = await self.groq.generate_structured_response(
                system_prompt=system_prompt,
                user_prompt=prompt,
                expected_fields=expected_fields,
                temperature=0.1,
                max_tokens=2500,
            )

            if not json_data:
                logger.warning("⚠️ AI parsing returned no data, using fallback")
                return self.basic_parser.parse(text, basic_info)

            # Sanitize LLM output
            safe_data = sanitize_llm_output(json_data)

            # Convert to ParsedData
            parsed = self.data_mapper.json_to_parsed_data(safe_data, basic_info)

            # Validate
            is_valid, errors = self.data_mapper.validate_parsed_data(parsed)

            if not is_valid:
                logger.warning(f"⚠️ AI parsing validation failed: {errors}")
                # Still return the parsed data, but log the issues

            logger.info("✅ AI parsing successful")

            return parsed

        except Exception as e:
            logger.error(f"❌ AI parsing failed: {e}, using fallback")
            return self.basic_parser.parse(text, basic_info)

    def get_quality_feedback(self, parsed: ParsedData) -> dict:
        """
        Get quality feedback for parsed resume
        
        Args:
            parsed: ParsedData instance
            
        Returns:
            Quality feedback dict
        """
        return self.quality_service.get_quality_feedback(parsed)

    def calculate_ats_score(self, parsed: ParsedData) -> dict:
        """
        Calculate ATS compatibility scores
        
        Args:
            parsed: ParsedData instance
            
        Returns:
            ATS scores dict
        """
        return self.quality_service.calculate_ats_score(parsed)

    def get_parser_stats(self) -> dict:
        """
        Get parser statistics
        
        Returns:
            Dict with parser stats
        """
        return {
            "ai_available": self.groq.is_available(),
            "groq_api_key_configured": bool(settings.GROQ_API_KEY),
            "fallback_parser_available": True,
            "template_version": self.prompt_templates.get_template_version(),
        }