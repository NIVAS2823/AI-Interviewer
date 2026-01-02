"""
Interview State Management
Maintains stateful memory for intelligent question generation
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CandidateInsight(BaseModel):
    """
    Single insight extracted from candidate's answer
    Used for follow-up questions
    """
    topic: str
    statement: str
    confidence_level: str  # "strong", "weak", "unclear"
    follow_up_potential: bool
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewMemory(BaseModel):
    """
    Persistent memory structure for interview agent
    Acts as agent's scratchpad
    """
    interview_id: str
    
    # Topics covered so far
    covered_topics: List[str] = Field(default_factory=list)
    
    # Key insights from candidate answers
    candidate_insights: List[CandidateInsight] = Field(default_factory=list)
    
    # Questions asked (for deduplication)
    asked_questions: List[str] = Field(default_factory=list)
    
    # Topics to explore (priority queue)
    topics_to_explore: List[str] = Field(default_factory=list)
    
    # Agent's reasoning (scratchpad)
    reasoning_history: List[str] = Field(default_factory=list)
    
    # Conversation turns
    turn_count: int = 0
    
    # Last answer summary
    last_answer_summary: Optional[str] = None
    
    # Candidate strengths/weaknesses identified
    identified_strengths: List[str] = Field(default_factory=list)
    identified_weaknesses: List[str] = Field(default_factory=list)


class InterviewState(BaseModel):
    """
    Complete interview state for LangGraph
    Includes both data and memory
    """
    # Metadata
    interview_id: str
    interview_type: str
    difficulty: str
    max_questions: int
    current_question_number: int = 0
    
    # Resume context (loaded once)
    candidate_name: Optional[str] = None
    candidate_skills: List[str] = Field(default_factory=list)
    candidate_experience: List[Dict[str, str]] = Field(default_factory=list)
    job_description: Optional[str] = None
    
    # Conversation history
    conversation: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Questions generated
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Memory (the magic!)
    memory: InterviewMemory
    
    # Current generation context
    current_context: Optional[str] = None
    
    # Error tracking
    errors: List[str] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True


class InterviewStateManager:
    """
    Manager for interview state operations
    Provides high-level operations on state
    """
    
    @staticmethod
    def create_initial_state(
        interview_id: str,
        interview_type: str,
        difficulty: str,
        max_questions: int,
        candidate_name: Optional[str] = None,
        candidate_skills: Optional[List[str]] = None,
        candidate_experience: Optional[List[Dict[str, str]]] = None,
        job_description: Optional[str] = None,
    ) -> InterviewState:
        """Create initial interview state"""
        memory = InterviewMemory(interview_id=interview_id)
        
        return InterviewState(
            interview_id=interview_id,
            interview_type=interview_type,
            difficulty=difficulty,
            max_questions=max_questions,
            candidate_name=candidate_name,
            candidate_skills=candidate_skills or [],
            candidate_experience=candidate_experience or [],
            job_description=job_description,
            memory=memory,
        )
    
    @staticmethod
    def add_question(state: InterviewState, question: Dict[str, Any]) -> InterviewState:
        """Add question to state"""
        state.questions.append(question)
        state.memory.asked_questions.append(question["question_text"])
        state.current_question_number = len(state.questions)
        
        # Add reasoning
        state.memory.reasoning_history.append(
            f"Q{state.current_question_number}: Asked about {question.get('category', 'general topic')}"
        )
        
        return state
    
    @staticmethod
    def add_answer(
        state: InterviewState, 
        answer: str,
        insights: Optional[List[CandidateInsight]] = None
    ) -> InterviewState:
        """Add candidate answer and extract insights"""
        state.conversation.append({
            "speaker": "candidate",
            "text": answer,
            "timestamp": datetime.utcnow(),
        })
        
        state.memory.turn_count += 1
        
        # Add insights if provided
        if insights:
            state.memory.candidate_insights.extend(insights)
            
            # Update topics to explore
            for insight in insights:
                if insight.follow_up_potential:
                    if insight.topic not in state.memory.topics_to_explore:
                        state.memory.topics_to_explore.append(insight.topic)
        
        return state
    
    @staticmethod
    def add_reasoning(state: InterviewState, reasoning: str) -> InterviewState:
        """Add agent reasoning to scratchpad"""
        state.memory.reasoning_history.append(reasoning)
        return state
    
    @staticmethod
    def get_context_summary(state: InterviewState) -> str:
        """Get summary of current context for next question"""
        lines = []
        
        lines.append(f"=== INTERVIEW PROGRESS ===")
        lines.append(f"Question {state.current_question_number}/{state.max_questions}")
        lines.append(f"Topics covered: {', '.join(state.memory.covered_topics[-5:])}")
        lines.append("")
        
        if state.memory.candidate_insights:
            lines.append("=== KEY INSIGHTS ===")
            recent_insights = state.memory.candidate_insights[-3:]
            for insight in recent_insights:
                lines.append(f"- {insight.topic}: {insight.statement} [{insight.confidence_level}]")
            lines.append("")
        
        if state.memory.topics_to_explore:
            lines.append("=== TOPICS TO EXPLORE ===")
            lines.append(", ".join(state.memory.topics_to_explore[:5]))
            lines.append("")
        
        if state.memory.reasoning_history:
            lines.append("=== AGENT REASONING ===")
            recent_reasoning = state.memory.reasoning_history[-3:]
            for r in recent_reasoning:
                lines.append(f"- {r}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def should_generate_followup(state: InterviewState) -> bool:
        """Determine if next question should be a follow-up"""
        # Follow up if we have insights with high follow-up potential
        if state.memory.candidate_insights:
            recent = state.memory.candidate_insights[-1]
            return recent.follow_up_potential and state.current_question_number > 1
        return False
    
    @staticmethod
    def get_followup_topic(state: InterviewState) -> Optional[str]:
        """Get topic for follow-up question"""
        if state.memory.topics_to_explore:
            return state.memory.topics_to_explore[0]
        return None
    
    @staticmethod
    def mark_topic_explored(state: InterviewState, topic: str) -> InterviewState:
        """Mark topic as explored"""
        if topic in state.memory.topics_to_explore:
            state.memory.topics_to_explore.remove(topic)
        
        if topic not in state.memory.covered_topics:
            state.memory.covered_topics.append(topic)
        
        return state
    
    @staticmethod
    def has_reached_max_questions(state: InterviewState) -> bool:
        """Check if max questions reached"""
        return state.current_question_number >= state.max_questions
    
    @staticmethod
    def to_dict(state: InterviewState) -> Dict[str, Any]:
        """Convert state to dict for serialization"""
        return state.model_dump()
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> InterviewState:
        """Load state from dict"""
        return InterviewState(**data)