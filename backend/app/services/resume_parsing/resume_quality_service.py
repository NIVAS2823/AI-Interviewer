"""
Resume Quality Service
Calculates quality and completeness scores for resumes
"""
import logging
from typing import Dict, Any

from app.models.resume import ParsedData

logger = logging.getLogger(__name__)


class ResumeQualityService:
    """
    Service for calculating resume quality metrics
    
    Responsibilities:
    - Calculate completeness scores
    - Calculate ATS compatibility scores
    - Provide quality feedback
    
    Does NOT:
    - Parse resumes
    - Extract data
    - Call APIs
    """

    # Scoring weights
    WEIGHTS = {
        "name": 10,
        "email": 8,
        "phone": 7,
        "summary_min": 10,
        "summary_good": 15,
        "skills_excellent": 20,
        "skills_good": 15,
        "skills_fair": 10,
        "experience_excellent": 25,
        "experience_good": 20,
        "experience_fair": 15,
        "education": 10,
        "projects": 5,
    }

    def __init__(self):
        """Initialize quality service"""
        logger.debug("Resume quality service initialized")

    def calculate_completeness_score(self, parsed: ParsedData) -> int:
        """
        Calculate resume completeness score (0-100)
        
        Args:
            parsed: ParsedData instance
            
        Returns:
            Score from 0 to 100
        """
        score = 0

        # Basic identity info (25 points max)
        if parsed.name:
            score += self.WEIGHTS["name"]
        if parsed.email:
            score += self.WEIGHTS["email"]
        if parsed.phone:
            score += self.WEIGHTS["phone"]

        # Summary quality (15 points max)
        if parsed.summary:
            summary_length = len(parsed.summary)
            if summary_length > 100:
                score += self.WEIGHTS["summary_good"]
            elif summary_length > 50:
                score += self.WEIGHTS["summary_min"]

        # Skills scoring (20 points max)
        total_skills = (
            len(parsed.skills.keywords) +
            len(parsed.skills.technical) +
            len(parsed.skills.soft) +
            len(parsed.skills.tools)
        )

        if total_skills >= 10:
            score += self.WEIGHTS["skills_excellent"]
        elif total_skills >= 5:
            score += self.WEIGHTS["skills_good"]
        elif total_skills > 0:
            score += self.WEIGHTS["skills_fair"]

        # Experience scoring (25 points max)
        experience_count = len(parsed.experience)
        if experience_count >= 3:
            score += self.WEIGHTS["experience_excellent"]
        elif experience_count >= 2:
            score += self.WEIGHTS["experience_good"]
        elif experience_count >= 1:
            score += self.WEIGHTS["experience_fair"]

        # Education (10 points max)
        if parsed.education:
            score += self.WEIGHTS["education"]

        # Projects (5 points max)
        if parsed.projects:
            score += self.WEIGHTS["projects"]

        # Cap at 100
        final_score = min(score, 100)

        logger.debug(f"Completeness score calculated: {final_score}/100")

        return final_score

    def calculate_ats_score(self, parsed: ParsedData) -> Dict[str, int]:
        """
        Calculate ATS compatibility scores
        
        Args:
            parsed: ParsedData instance
            
        Returns:
            Dict with various ATS scores
        """
        scores = {
            "overall_score": 0,
            "skills_score": 0,
            "experience_score": 0,
            "education_score": 0,
            "projects_score": 0,
            "keyword_match_percentage": 0,
        }

        # Skills score (0-100)
        total_skills = (
            len(parsed.skills.keywords) +
            len(parsed.skills.technical) +
            len(parsed.skills.soft) +
            len(parsed.skills.tools)
        )
        scores["skills_score"] = min(total_skills * 5, 100)  # 20 skills = 100 points

        # Experience score (0-100)
        experience_count = len(parsed.experience)
        scores["experience_score"] = min(experience_count * 25, 100)  # 4+ experiences = 100

        # Education score (0-100)
        education_count = len(parsed.education)
        scores["education_score"] = min(education_count * 50, 100)  # 2+ degrees = 100

        # Projects score (0-100)
        projects_count = len(parsed.projects)
        scores["projects_score"] = min(projects_count * 20, 100)  # 5+ projects = 100

        # Overall score (weighted average)
        scores["overall_score"] = int(
            scores["skills_score"] * 0.4 +
            scores["experience_score"] * 0.3 +
            scores["education_score"] * 0.15 +
            scores["projects_score"] * 0.15
        )

        # Keyword match (simplified)
        scores["keyword_match_percentage"] = min(
            len(parsed.skills.keywords) * 5, 100
        )

        logger.debug(f"ATS score calculated: {scores['overall_score']}/100")

        return scores

    def get_quality_feedback(self, parsed: ParsedData) -> Dict[str, Any]:
        """
        Get detailed quality feedback
        
        Args:
            parsed: ParsedData instance
            
        Returns:
            Dict with feedback and suggestions
        """
        completeness = self.calculate_completeness_score(parsed)
        ats_scores = self.calculate_ats_score(parsed)

        suggestions = []
        strengths = []

        # Check what's missing
        if not parsed.name:
            suggestions.append("Add your full name")
        else:
            strengths.append("Name present")

        if not parsed.email:
            suggestions.append("Add email address")
        else:
            strengths.append("Contact email provided")

        if not parsed.phone:
            suggestions.append("Add phone number")
        else:
            strengths.append("Phone number provided")

        if not parsed.summary or len(parsed.summary) < 50:
            suggestions.append("Add a professional summary (100-200 words)")
        else:
            strengths.append("Professional summary included")

        # Skills
        total_skills = (
            len(parsed.skills.keywords) +
            len(parsed.skills.technical) +
            len(parsed.skills.soft)
        )
        if total_skills < 5:
            suggestions.append("Add more skills (aim for 10-15 relevant skills)")
        elif total_skills >= 10:
            strengths.append(f"Strong skills section ({total_skills} skills)")

        # Experience
        if len(parsed.experience) == 0:
            suggestions.append("Add work experience")
        elif len(parsed.experience) < 2:
            suggestions.append("Add more work experience entries")
        else:
            strengths.append(f"{len(parsed.experience)} work experiences listed")

        # Education
        if not parsed.education:
            suggestions.append("Add education details")
        else:
            strengths.append("Education information provided")

        # Projects
        if not parsed.projects:
            suggestions.append("Consider adding relevant projects")
        elif len(parsed.projects) >= 3:
            strengths.append(f"{len(parsed.projects)} projects showcased")

        # Overall rating
        if completeness >= 80:
            rating = "Excellent"
        elif completeness >= 60:
            rating = "Good"
        elif completeness >= 40:
            rating = "Fair"
        else:
            rating = "Needs Improvement"

        return {
            "completeness_score": completeness,
            "ats_scores": ats_scores,
            "rating": rating,
            "strengths": strengths,
            "suggestions": suggestions,
            "is_complete": completeness >= 70,
        }

    def compare_resumes(self, resume1: ParsedData, resume2: ParsedData) -> Dict[str, Any]:
        """
        Compare two resumes
        
        Args:
            resume1: First resume
            resume2: Second resume
            
        Returns:
            Comparison dict
        """
        score1 = self.calculate_completeness_score(resume1)
        score2 = self.calculate_completeness_score(resume2)

        return {
            "resume1_score": score1,
            "resume2_score": score2,
            "difference": abs(score1 - score2),
            "better_resume": "resume1" if score1 > score2 else "resume2" if score2 > score1 else "tie",
        }

    def get_score_breakdown(self, parsed: ParsedData) -> Dict[str, int]:
        """
        Get detailed score breakdown
        
        Args:
            parsed: ParsedData instance
            
        Returns:
            Dict with score components
        """
        breakdown = {
            "identity_score": 0,
            "summary_score": 0,
            "skills_score": 0,
            "experience_score": 0,
            "education_score": 0,
            "projects_score": 0,
        }

        # Identity
        if parsed.name:
            breakdown["identity_score"] += 10
        if parsed.email:
            breakdown["identity_score"] += 8
        if parsed.phone:
            breakdown["identity_score"] += 7

        # Summary
        if parsed.summary and len(parsed.summary) > 100:
            breakdown["summary_score"] = 15
        elif parsed.summary and len(parsed.summary) > 50:
            breakdown["summary_score"] = 10

        # Skills
        total_skills = len(parsed.skills.keywords) + len(parsed.skills.technical)
        breakdown["skills_score"] = min(total_skills * 2, 20)

        # Experience
        breakdown["experience_score"] = min(len(parsed.experience) * 8, 25)

        # Education
        breakdown["education_score"] = min(len(parsed.education) * 5, 10)

        # Projects
        breakdown["projects_score"] = min(len(parsed.projects), 5)

        return breakdown