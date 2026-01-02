"""
Basic Resume Parser
Fallback parser using keyword extraction when AI is unavailable
"""
import logging
import re
from typing import Dict, List

from app.models.resume import ParsedData, Skills

logger = logging.getLogger(__name__)


class BasicResumeParser:
    """
    Basic keyword-based resume parser
    
    Responsibilities:
    - Extract basic info using patterns
    - Keyword matching for skills
    - Simple section detection
    
    Does NOT:
    - Use AI/LLM
    - Parse complex structures
    - Calculate scores
    """

    # Common technical skills keywords
    TECHNICAL_KEYWORDS = [
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "Ruby",
        "PHP", "Swift", "Kotlin", "React", "Angular", "Vue", "Node.js", "Express",
        "Django", "Flask", "FastAPI", "Spring", "ASP.NET",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform",
        "Git", "CI/CD", "Jenkins", "GitHub Actions",
        "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning", "AI",
        "REST API", "GraphQL", "WebSocket", "Microservices",
        "HTML", "CSS", "SASS", "Tailwind", "Bootstrap",
        "SQL", "NoSQL", "Linux", "Bash", "PowerShell",
    ]

    # Soft skills keywords
    SOFT_SKILLS = [
        "Leadership", "Communication", "Teamwork", "Problem Solving",
        "Critical Thinking", "Collaboration", "Adaptability", "Time Management",
        "Project Management", "Agile", "Scrum", "Mentoring",
    ]

    # Tools keywords
    TOOLS = [
        "VS Code", "IntelliJ", "PyCharm", "Jupyter", "Postman",
        "Jira", "Confluence", "Slack", "Figma", "Sketch",
        "Excel", "PowerPoint", "Tableau", "Power BI",
    ]

    def __init__(self):
        """Initialize basic parser"""
        logger.debug("Basic resume parser initialized")

    def parse(self, text: str, basic_info: Dict) -> ParsedData:
        """
        Parse resume using basic keyword matching
        
        Args:
            text: Resume text
            basic_info: Basic info extracted from PDF
            
        Returns:
            ParsedData instance
        """
        logger.info("🔄 Using fallback basic parser")

        # Extract name from first line if not in basic_info
        name = self._extract_name(text, basic_info)

        # Extract skills
        skills = self._extract_skills(text)

        # Create parsed data
        parsed = ParsedData(
            name=name,
            email=basic_info.get("email"),
            phone=basic_info.get("phone"),
            summary=self._extract_summary(text),
            skills=skills,
            experience=[],  # Basic parser doesn't extract structured experience
            education=[],   # Basic parser doesn't extract structured education
            certifications=self._extract_certifications(text),
            projects=[],
            languages=[]
        )

        logger.info(f"✅ Basic parsing complete: {len(skills.technical)} technical skills found")

        return parsed

    def _extract_name(self, text: str, basic_info: Dict) -> str:
        """Extract name from text"""
        # Try basic_info first
        if basic_info.get("name"):
            return basic_info["name"]

        # Try first line
        lines = text.split("\n")
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 50 and not any(kw in line.lower() for kw in ["email", "phone", "linkedin"]):
                return line

        return ""

    def _extract_skills(self, text: str) -> Skills:
        """
        Extract skills using keyword matching
        
        Args:
            text: Resume text
            
        Returns:
            Skills object
        """
        text_lower = text.lower()

        # Find technical skills
        technical = []
        for skill in self.TECHNICAL_KEYWORDS:
            if skill.lower() in text_lower:
                technical.append(skill)

        # Find soft skills
        soft = []
        for skill in self.SOFT_SKILLS:
            if skill.lower() in text_lower:
                soft.append(skill)

        # Find tools
        tools = []
        for tool in self.TOOLS:
            if tool.lower() in text_lower:
                tools.append(tool)

        # Combine unique keywords
        keywords = list(set(technical + soft + tools))

        return Skills(
            keywords=keywords[:20],  # Top 20
            technical=technical[:15],
            soft=soft[:10],
            tools=tools[:10],
            ats_top_matches=[],
            keyword_density_score=0,
        )

    def _extract_summary(self, text: str) -> str:
        """
        Extract summary/objective section
        
        Args:
            text: Resume text
            
        Returns:
            Summary text or empty string
        """
        # Look for summary section
        summary_patterns = [
            r"summary[:\s]+(.*?)(?=\n\n|\nexperience|\neducation|$)",
            r"objective[:\s]+(.*?)(?=\n\n|\nexperience|\neducation|$)",
            r"profile[:\s]+(.*?)(?=\n\n|\nexperience|\neducation|$)",
        ]

        text_lower = text.lower()

        for pattern in summary_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                summary = match.group(1).strip()
                # Clean up
                summary = re.sub(r'\s+', ' ', summary)
                if len(summary) > 50:
                    return summary[:500]  # Max 500 chars

        return ""

    def _extract_certifications(self, text: str) -> List[str]:
        """
        Extract certifications
        
        Args:
            text: Resume text
            
        Returns:
            List of certifications
        """
        certifications = []

        # Common certification patterns
        cert_keywords = [
            "AWS Certified", "Google Certified", "Microsoft Certified",
            "PMP", "CISSP", "CCNA", "CCNP", "CKA", "CKAD",
            "Scrum Master", "Product Owner", "Six Sigma",
        ]

        text_lower = text.lower()

        for cert in cert_keywords:
            if cert.lower() in text_lower:
                certifications.append(cert)

        return certifications[:10]  # Max 10

    def extract_years_of_experience(self, text: str) -> int:
        """
        Estimate years of experience from text
        
        Args:
            text: Resume text
            
        Returns:
            Estimated years
        """
        # Look for patterns like "5 years of experience", "5+ years"
        patterns = [
            r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
            r'experience[:\s]+(\d+)\+?\s*years?',
        ]

        text_lower = text.lower()

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass

        return 0

    def detect_sections(self, text: str) -> Dict[str, bool]:
        """
        Detect which sections are present
        
        Args:
            text: Resume text
            
        Returns:
            Dict with section presence flags
        """
        text_lower = text.lower()

        sections = {
            "summary": any(kw in text_lower for kw in ["summary", "objective", "profile"]),
            "skills": "skill" in text_lower,
            "experience": "experience" in text_lower or "work history" in text_lower,
            "education": "education" in text_lower,
            "projects": "project" in text_lower,
            "certifications": "certification" in text_lower or "certificate" in text_lower,
        }

        return sections

    def estimate_completeness(self, text: str) -> float:
        """
        Estimate resume completeness
        
        Args:
            text: Resume text
            
        Returns:
            Completeness score (0-1)
        """
        sections = self.detect_sections(text)
        present_count = sum(sections.values())
        total_sections = len(sections)

        return present_count / total_sections if total_sections > 0 else 0