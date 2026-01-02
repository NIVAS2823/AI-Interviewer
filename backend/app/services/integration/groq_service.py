"""
Groq LLM Integration Service
Handles all Groq API interactions with proper error handling
"""
from typing import Optional, Dict, Any, List
import json
import re
import logging

from app.core.config import settings
from app.utils.json_utils import extract_single_json

logger = logging.getLogger(__name__)


class GroqService:
    """
    Wrapper for Groq LLM API
    Centralizes all LLM calls with consistent error handling
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize Groq service
        
        Args:
            api_key: Groq API key (uses settings if not provided)
            model: Model to use for completions
        """
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy-load Groq client"""
        if self._client is None and self.api_key:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
        return self._client

    def is_available(self) -> bool:
        """Check if Groq API is configured and available"""
        return bool(self.api_key and self.client)

    async def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        expected_fields: List[str],
        temperature: float = 0.8,
        max_tokens: int = 300,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate structured JSON response from LLM
        
        Args:
            system_prompt: System instructions
            user_prompt: User query/context
            expected_fields: List of required JSON fields
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Parsed JSON dict or None on failure
        """
        if not self.is_available():
            logger.error("Groq API not configured")
            return None

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response_text = response.choices[0].message.content.strip()
            logger.debug(f"Raw LLM response: {response_text[:200]}...")

            # Extract JSON from response
            json_data = self._extract_json(response_text)

            if not json_data:
                logger.error("Failed to extract JSON from LLM response")
                return None

            # Validate required fields
            missing_fields = [f for f in expected_fields if f not in json_data]
            if missing_fields:
                logger.warning(f"Missing fields in LLM response: {missing_fields}")
                return None

            logger.info("✅ Successfully generated structured response")
            return json_data

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 200,
    ) -> Optional[str]:
        """
        Generate simple text response from LLM
        
        Args:
            system_prompt: System instructions
            user_prompt: User query
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text or None on failure
        """
        if not self.is_available():
            logger.error("Groq API not configured")
            return None

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

    async def generate_interview_answer(
        self,
        question: str,
        category: str,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate simulated candidate answer for interview question
        
        Args:
            question: Interview question
            category: Question category (technical, behavioral, etc.)
            temperature: Sampling temperature
            
        Returns:
            Generated answer text (fallback if API fails)
        """
        system_prompt = (
            f"You are a job candidate in an interview. "
            f"Give a polished, professional 2-3 sentence answer to a {category} interview question. "
            f"Sound natural and conversational."
        )

        answer = await self.generate_text(
            system_prompt=system_prompt,
            user_prompt=question,
            temperature=temperature,
            max_tokens=200,
        )

        # Fallback answer if API fails
        if not answer:
            logger.warning("Using fallback answer due to API failure")
            return (
                "Based on my experience, I would analyze the requirements "
                "and implement a clear, maintainable solution following best practices."
            )

        return answer

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response (handles markdown wrapping)
        
        Args:
            text: Raw LLM response text
            
        Returns:
            Parsed JSON dict or None
        """
        # Method 1: Try the utility function
        try:
            return extract_single_json(text)
        except Exception as e:
            logger.debug(f"extract_single_json failed: {e}")

        # Method 2: Regex for JSON object
        try:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
        except Exception as e:
            logger.debug(f"Regex extraction failed: {e}")

        # Method 3: Try parsing entire text as JSON
        try:
            return json.loads(text)
        except Exception as e:
            logger.debug(f"Direct JSON parse failed: {e}")

        return None

    async def generate_question_json(
        self,
        context: str,
        interview_type: str,
        difficulty: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate interview question in JSON format
        
        Args:
            context: Full context for question generation
            interview_type: Type of interview
            difficulty: Difficulty level
            
        Returns:
            Question JSON dict or None
        """
        system_prompt = """You are an expert technical interviewer. Generate ONE interview question based on the context provided.

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{
  "question_text": "Your question here",
  "category": "technical|behavioral|hr",
  "difficulty": "easy|medium|hard",
  "expected_topics": ["topic1", "topic2"]
}"""

        return await self.generate_structured_response(
            system_prompt=system_prompt,
            user_prompt=context,
            expected_fields=["question_text", "category", "difficulty", "expected_topics"],
            temperature=0.8,
            max_tokens=300,
        )

    async def generate_evaluation_json(
        self,
        conversation: str,
        questions: str,
        interview_type: str,
        difficulty: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate interview evaluation in JSON format
        
        Args:
            conversation: Formatted conversation history
            questions: Formatted question list
            interview_type: Type of interview
            difficulty: Difficulty level
            
        Returns:
            Evaluation JSON dict or None
        """
        system_prompt = """You are an expert interview evaluator. Analyze the interview and provide a comprehensive evaluation.

Return ONLY valid JSON (no markdown):
{
  "scores": {
    "overall_score": 0-100,
    "technical_score": 0-100,
    "communication_score": 0-100,
    "confidence_score": 0-100,
    "behavioral_score": 0-100
  },
  "sentiment": {
    "positive": 0.0-1.0,
    "neutral": 0.0-1.0,
    "negative": 0.0-1.0
  },
  "strengths": ["strength1", "strength2"],
  "improvements": ["improvement1", "improvement2"],
  "detailed_feedback": "overall feedback text",
  "question_scores": []
}"""

        context = f"""Interview Type: {interview_type}
Difficulty: {difficulty}

{questions}

{conversation}"""

        return await self.generate_structured_response(
            system_prompt=system_prompt,
            user_prompt=context,
            expected_fields=["scores", "strengths", "improvements", "detailed_feedback"],
            temperature=0.5,
            max_tokens=1500,
        )