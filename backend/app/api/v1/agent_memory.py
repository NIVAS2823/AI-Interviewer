"""
Agent Memory API Endpoint
Allows viewing agent's memory and reasoning for debugging/analytics
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.core.database import get_database
from app.services.interview_engine import InterviewEngineService

router = APIRouter(prefix="/agent-memory", tags=["Agent Memory"])


@router.get("/{interview_id}")
async def get_agent_memory(
    interview_id: str,
    db=Depends(get_database),
) -> Dict[str, Any]:
    """
    Get agent's memory summary for an interview
    
    Shows:
    - Topics covered
    - Topics to explore
    - Insights extracted from answers
    - Agent's reasoning history (scratchpad)
    
    Useful for:
    - Debugging interview flow
    - Understanding follow-up logic
    - Analytics on interview quality
    """
    engine = InterviewEngineService()
    
    try:
        memory_summary = await engine.get_agent_memory_summary(interview_id, db)
        return memory_summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent memory: {str(e)}")


@router.get("/{interview_id}/insights")
async def get_candidate_insights(
    interview_id: str,
    db=Depends(get_database),
) -> Dict[str, Any]:
    """
    Get all insights extracted from candidate's answers
    
    Returns:
    - List of insights with topics and confidence levels
    - Follow-up potential flags
    - Timestamps
    """
    from app.services.repositories.repository_factory import get_repositories
    
    repos = get_repositories(db)
    state = await repos.interview_state.load_state(interview_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Agent state not found")
    
    insights = [
        {
            "topic": insight.topic,
            "statement": insight.statement,
            "confidence_level": insight.confidence_level,
            "follow_up_potential": insight.follow_up_potential,
            "extracted_at": insight.extracted_at.isoformat(),
        }
        for insight in state.memory.candidate_insights
    ]
    
    return {
        "interview_id": interview_id,
        "total_insights": len(insights),
        "insights": insights,
    }


@router.get("/{interview_id}/reasoning")
async def get_agent_reasoning(
    interview_id: str,
    db=Depends(get_database),
) -> Dict[str, Any]:
    """
    Get agent's reasoning history (scratchpad)
    
    Shows step-by-step decisions made by the agent
    """
    from app.services.repositories.repository_factory import get_repositories
    
    repos = get_repositories(db)
    state = await repos.interview_state.load_state(interview_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Agent state not found")
    
    return {
        "interview_id": interview_id,
        "total_steps": len(state.memory.reasoning_history),
        "reasoning_history": state.memory.reasoning_history,
        "current_question": state.current_question_number,
        "max_questions": state.max_questions,
    }