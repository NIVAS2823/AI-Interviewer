"""
Context Builder Service
Builds context for dynamic question generation
Pure business logic with no external dependencies
"""
from typing import List, Dict, Any
import logging

from app.models.resume import ParsedData

logger = logging.getLogger(__name__)


class QuestionContextBuilder:
    """
    Builds rich context for AI question generation
    Follows single responsibility: context construction only
    """

    @staticmethod
    def extract_top_skills(skills_obj, max_skills: int = 10) -> List[str]:
        """
        Extract top skills from resume skills object
        
        Args:
            skills_obj: Skills object from ParsedData
            max_skills: Maximum number of skills to return
            
        Returns:
            List of unique skill strings
        """
        if not skills_obj:
            return []

        # Flatten all skill categories
        all_skills = (
            (skills_obj.keywords or []) +
            (skills_obj.technical or []) +
            (skills_obj.soft or []) +
            (skills_obj.tools or [])
        )

        # Return unique skills (preserving order)
        return list(dict.fromkeys(all_skills))[:max_skills]

    @staticmethod
    def build_resume_context(parsed_resume: ParsedData) -> str:
        """
        Build resume section of context
        
        Args:
            parsed_resume: ParsedData model instance
            
        Returns:
            Formatted resume context string
        """
        lines = ["=== CANDIDATE RESUME ==="]

        if parsed_resume.name:
            lines.append(f"Name: {parsed_resume.name}")

        if parsed_resume.skills:
            skills = QuestionContextBuilder.extract_top_skills(parsed_resume.skills)
            if skills:
                lines.append(f"Skills: {', '.join(skills)}")

        if parsed_resume.experience:
            lines.append("Experience:")
            for exp in parsed_resume.experience[:3]:  # Top 3 experiences
                lines.append(f"  - {exp.role} at {exp.company}")

        if parsed_resume.education:
            lines.append("Education:")
            for edu in parsed_resume.education[:2]:  # Top 2 education entries
                lines.append(f"  - {edu.degree} in {edu.field}")

        lines.append("")  # Empty line separator
        return "\n".join(lines)

    @staticmethod
    def build_conversation_context(
        conversation: List[Dict[str, Any]],
        max_messages: int = 8
    ) -> str:
        """
        Build conversation history section
        
        Args:
            conversation: List of conversation message dicts
            max_messages: Maximum recent messages to include
            
        Returns:
            Formatted conversation context string
        """
        if not conversation:
            return ""

        lines = ["=== PREVIOUS CONVERSATION ==="]

        # Get recent conversation (last N messages)
        recent_conv = conversation[-(min(max_messages, len(conversation))):]

        for msg in recent_conv:
            speaker = "INTERVIEWER" if msg.get("speaker") == "ai" else "CANDIDATE"
            text = msg.get("text", "")
            
            # Truncate long messages
            text_preview = text[:100] + "..." if len(text) > 100 else text
            lines.append(f"{speaker}: {text_preview}")

        lines.append("")  # Empty line separator
        return "\n".join(lines)

    @staticmethod
    def build_job_description_context(job_description: str, max_length: int = 500) -> str:
        """
        Build job description section
        
        Args:
            job_description: Job description text
            max_length: Maximum length to include
            
        Returns:
            Formatted job description context string
        """
        if not job_description:
            return ""

        lines = ["=== JOB DESCRIPTION ==="]
        
        # Truncate if too long
        truncated_jd = job_description[:max_length]
        if len(job_description) > max_length:
            truncated_jd += "..."
        
        lines.append(truncated_jd)
        lines.append("")  # Empty line separator
        
        return "\n".join(lines)

    @staticmethod
    def build_task_instructions(
        question_number: int,
        total_questions: int,
        has_job_description: bool
    ) -> str:
        """
        Build task-specific instructions based on question position
        
        Args:
            question_number: Current question number (1-indexed)
            total_questions: Total number of questions planned
            has_job_description: Whether job description is available
            
        Returns:
            Formatted task instructions string
        """
        lines = ["=== TASK ==="]

        if question_number == 1:
            # Opening question
            lines.extend([
                "Generate a warm opening question that:",
                "- Puts the candidate at ease",
                "- Relates to their background",
            ])
            if has_job_description:
                lines.append("- Connects to the job requirements")

        elif question_number == total_questions:
            # Closing question
            lines.extend([
                "Generate a closing question that:",
                "- Wraps up the interview naturally",
                "- Gives candidate chance to highlight strengths",
                "- Shows their motivation",
            ])

        else:
            # Middle questions
            lines.extend([
                "Generate the next question that:",
                "- Builds on the candidate's previous answers",
                "- Explores topics they mentioned",
            ])
            if has_job_description:
                lines.append("- Assesses fit for the job requirements")
            lines.append("- Is appropriate for the difficulty level")

        return "\n".join(lines)

    def build_question_generation_context(
        self,
        parsed_resume: ParsedData,
        interview_type: str,
        difficulty: str,
        question_number: int,
        total_questions: int,
        conversation: List[Dict[str, Any]] = None,
        job_description: str = None,
    ) -> str:
        """
        Build complete context for question generation
        
        Args:
            parsed_resume: Parsed resume data
            interview_type: Type of interview
            difficulty: Difficulty level
            question_number: Current question number (1-indexed)
            total_questions: Total questions planned
            conversation: Previous conversation messages
            job_description: Optional job description
            
        Returns:
            Complete formatted context string for LLM
        """
        context_parts = []

        # Header
        context_parts.append("=== INTERVIEW CONTEXT ===")
        context_parts.append(f"Question {question_number} of {total_questions}")
        context_parts.append(f"Interview Type: {interview_type}")
        context_parts.append(f"Difficulty: {difficulty}")
        context_parts.append("")

        # Resume
        context_parts.append(self.build_resume_context(parsed_resume))

        # Job description (if provided)
        if job_description:
            context_parts.append(self.build_job_description_context(job_description))

        # Conversation history (if exists)
        if conversation:
            context_parts.append(self.build_conversation_context(conversation))

        # Task instructions
        context_parts.append(
            self.build_task_instructions(
                question_number=question_number,
                total_questions=total_questions,
                has_job_description=bool(job_description)
            )
        )

        return "\n".join(context_parts)

    def build_candidate_info_dict(self, parsed_resume: ParsedData) -> Dict[str, Any]:
        """
        Build candidate info dictionary for VideoSDK agent
        
        Args:
            parsed_resume: Parsed resume data
            
        Returns:
            Dict with candidate information
        """
        return {
            "name": parsed_resume.name or "Candidate",
            "skills": self.extract_top_skills(parsed_resume.skills),
            "experience_years": len(parsed_resume.experience) if parsed_resume.experience else 0,
            "education": [
                f"{edu.degree} in {edu.field}"
                for edu in (parsed_resume.education[:2] if parsed_resume.education else [])
            ],
        }