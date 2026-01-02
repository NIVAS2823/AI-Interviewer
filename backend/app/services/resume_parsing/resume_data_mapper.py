"""
Resume Data Mapper
Converts JSON data to Pydantic models
"""
import logging
from typing import Dict, Any

from app.models.resume import (
    ParsedData,
    WorkExperience,
    Education,
    Project,
    Skills,
)

logger = logging.getLogger(__name__)


class ResumeDataMapper:
    """
    Service for mapping JSON data to Pydantic models
    
    Responsibilities:
    - Convert JSON to ParsedData
    - Handle missing/invalid fields
    - Validate data structures
    
    Does NOT:
    - Parse resumes
    - Call APIs
    - Calculate scores
    """

    def __init__(self):
        """Initialize data mapper"""
        logger.debug("Resume data mapper initialized")

    def json_to_parsed_data(
        self,
        data: Dict[str, Any],
        basic_info: Dict[str, Any],
    ) -> ParsedData:
        """
        Convert JSON data to ParsedData model
        
        Args:
            data: JSON data from LLM
            basic_info: Basic info from PDF parser
            
        Returns:
            ParsedData instance
        """
        try:
            # Map experience
            experience = self._map_experience(data.get("experience", []))

            # Map education
            education = self._map_education(data.get("education", []))

            # Map projects
            projects = self._map_projects(data.get("projects", []))

            # Map skills
            skills = self._map_skills(data.get("skills", {}))

            # Create ParsedData
            parsed = ParsedData(
                name=data.get("name") or basic_info.get("name") or "",
                email=data.get("email") or basic_info.get("email") or "",
                phone=data.get("phone") or basic_info.get("phone") or "",
                linkedin=data.get("linkedin") or "",
                github=data.get("github") or "",
                portfolio=data.get("portfolio") or "",
                summary=data.get("summary") or "",
                skills=skills,
                experience=experience,
                education=education,
                certifications=data.get("certifications", []) or [],
                projects=projects,
                languages=data.get("languages", []) or [],
                raw_text=None,
            )

            logger.info(
                f"✅ Mapped resume data: {len(experience)} experiences, "
                f"{len(education)} education, {len(projects)} projects"
            )

            return parsed

        except Exception as e:
            logger.exception(f"❌ Failed to map JSON to ParsedData: {e}")
            raise ValueError(f"Data mapping failed: {str(e)}")

    def _map_experience(self, experience_data: list) -> list[WorkExperience]:
        """
        Map experience data to WorkExperience models
        
        Args:
            experience_data: List of experience dicts
            
        Returns:
            List of WorkExperience instances
        """
        experience = []

        for e in experience_data:
            if not isinstance(e, dict):
                logger.warning(f"Skipping invalid experience entry: {type(e)}")
                continue

            try:
                work_exp = WorkExperience(
                    company=e.get("company") or "",
                    role=e.get("role") or "",
                    location=e.get("location") or "",
                    duration=e.get("duration") or "",
                    start_date=e.get("start_date") or "",
                    end_date=e.get("end_date") or "",
                    description=e.get("description") or "",
                    achievements=e.get("achievements", []) or [],
                    technologies=e.get("technologies", []) or [],
                )
                experience.append(work_exp)
            except Exception as ex:
                logger.warning(f"Failed to parse experience entry: {ex}")

        return experience

    def _map_education(self, education_data: list) -> list[Education]:
        """
        Map education data to Education models
        
        Args:
            education_data: List of education dicts
            
        Returns:
            List of Education instances
        """
        education = []

        for e in education_data:
            if not isinstance(e, dict):
                logger.warning(f"Skipping invalid education entry: {type(e)}")
                continue

            try:
                edu = Education(
                    institution=e.get("institution") or "",
                    degree=e.get("degree") or "",
                    field=e.get("field") or "",
                    start_year=e.get("start_year") or "",
                    end_year=e.get("end_year") or "",
                    year=e.get("year") or "",
                    gpa=e.get("cgpa") or e.get("gpa") or "",
                )
                education.append(edu)
            except Exception as ex:
                logger.warning(f"Failed to parse education entry: {ex}")

        return education

    def _map_projects(self, projects_data: list) -> list[Project]:
        """
        Map projects data to Project models
        
        Args:
            projects_data: List of project dicts
            
        Returns:
            List of Project instances
        """
        projects = []

        for p in projects_data:
            if not isinstance(p, dict):
                logger.warning(f"Skipping invalid project entry: {type(p)}")
                continue

            try:
                project = Project(
                    name=p.get("title") or p.get("name") or "",
                    description=p.get("description") or "",
                    technologies=p.get("technologies", []) or [],
                    url=p.get("url"),
                    impact=p.get("impact") or "",
                )
                projects.append(project)
            except Exception as ex:
                logger.warning(f"Failed to parse project entry: {ex}")

        return projects

    def _map_skills(self, skills_data: Dict[str, Any]) -> Skills:
        """
        Map skills data to Skills model
        
        Args:
            skills_data: Skills dict
            
        Returns:
            Skills instance
        """
        try:
            skills = Skills(
                keywords=skills_data.get("keywords", []) or [],
                technical=skills_data.get("technical", []) or [],
                soft=skills_data.get("soft", []) or [],
                tools=skills_data.get("tools", []) or [],
                ats_top_matches=skills_data.get("ats_top_matches", []) or [],
                keyword_density_score=skills_data.get("keyword_density_score", 0) or 0,
            )
            return skills
        except Exception as e:
            logger.warning(f"Failed to parse skills, using defaults: {e}")
            return Skills(
                keywords=[],
                technical=[],
                soft=[],
                tools=[],
                ats_top_matches=[],
                keyword_density_score=0,
            )

    def validate_parsed_data(self, parsed: ParsedData) -> tuple[bool, list[str]]:
        """
        Validate parsed data
        
        Args:
            parsed: ParsedData instance
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        if not parsed.name:
            errors.append("Missing name")

        if not parsed.email and not parsed.phone:
            errors.append("Missing both email and phone")

        # Check data quality
        total_skills = (
            len(parsed.skills.keywords) +
            len(parsed.skills.technical) +
            len(parsed.skills.soft)
        )

        if total_skills == 0:
            errors.append("No skills found")

        if len(parsed.experience) == 0 and len(parsed.education) == 0:
            errors.append("No experience or education found")

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning(f"⚠️ Validation failed: {', '.join(errors)}")

        return is_valid, errors

    def merge_with_basic_info(
        self,
        parsed: ParsedData,
        basic_info: Dict[str, Any],
    ) -> ParsedData:
        """
        Merge parsed data with basic info (fill gaps)
        
        Args:
            parsed: ParsedData instance
            basic_info: Basic info dict
            
        Returns:
            Updated ParsedData
        """
        # Fill missing contact info
        if not parsed.name and basic_info.get("name"):
            parsed.name = basic_info["name"]

        if not parsed.email and basic_info.get("email"):
            parsed.email = basic_info["email"]

        if not parsed.phone and basic_info.get("phone"):
            parsed.phone = basic_info["phone"]

        logger.debug("Merged parsed data with basic info")

        return parsed