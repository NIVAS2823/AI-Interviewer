"""
Repository Factory
Provides dependency injection for repositories
"""
from app.services.repositories.interview_repository import InterviewRepository
from app.services.repositories.conversation_repository import ConversationRepository
from app.services.repositories.resume_repository import ResumeRepository
from app.services.repositories.interview_state_repository import InterviewStateRepository


class RepositoryFactory:
    """
    Factory for creating repository instances
    Simplifies dependency injection
    """

    def __init__(self, db):
        """
        Initialize factory with database connection
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self._interview_repo = None
        self._conversation_repo = None
        self._resume_repo = None
        self._state_repo = None

    @property
    def interviews(self) -> InterviewRepository:
        """Get or create InterviewRepository instance"""
        if self._interview_repo is None:
            self._interview_repo = InterviewRepository(self.db)
        return self._interview_repo

    @property
    def conversations(self) -> ConversationRepository:
        """Get or create ConversationRepository instance"""
        if self._conversation_repo is None:
            self._conversation_repo = ConversationRepository(self.db)
        return self._conversation_repo

    @property
    def resumes(self) -> ResumeRepository:
        """Get or create ResumeRepository instance"""
        if self._resume_repo is None:
            self._resume_repo = ResumeRepository(self.db)
        return self._resume_repo

    @property
    def interview_state(self) -> InterviewStateRepository:
        """Get or create InterviewStateRepository instance"""
        if self._state_repo is None:
            self._state_repo = InterviewStateRepository(self.db)
        return self._state_repo


def get_repositories(db) -> RepositoryFactory:
    """
    Convenience function to get repository factory
    
    Usage in services:
        repos = get_repositories(db)
        interview = await repos.interviews.get_interview(interview_id)
        
    Args:
        db: MongoDB database instance
        
    Returns:
        RepositoryFactory instance
    """
    return RepositoryFactory(db)