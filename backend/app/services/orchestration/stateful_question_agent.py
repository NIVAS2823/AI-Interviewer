"""
Stateful Question Generation Agent
Uses LangGraph for stateful interview management with memory
"""
from typing import Optional, Dict, Any, List
import logging
import json

from app.services.orchestration.interview_state import (
    InterviewState,
    InterviewStateManager,
    CandidateInsight,
)
from app.services.integration.groq_service import GroqService
from app.models.interview import Question

logger = logging.getLogger(__name__)


class StatefulQuestionAgent:
    """
    Stateful agent that remembers previous answers and generates intelligent follow-ups
    Uses agent scratchpad pattern for reasoning
    """

    def __init__(self, groq_service: Optional[GroqService] = None):
        """
        Initialize stateful agent
        
        Args:
            groq_service: LLM service for generation
        """
        self.groq = groq_service or GroqService()
        self.state_manager = InterviewStateManager()

    async def generate_next_question_stateful(
        self,
        state: InterviewState,
    ) -> tuple[Optional[Question], InterviewState]:
        """
        Generate next question with full state awareness
        
        Args:
            state: Current interview state with memory
            
        Returns:
            Tuple of (generated question, updated state)
        """
        if self.state_manager.has_reached_max_questions(state):
            logger.info("Max questions reached")
            return None, state

        # Check if we should do a follow-up
        should_followup = self.state_manager.should_generate_followup(state)
        followup_topic = self.state_manager.get_followup_topic(state)

        # Build context with memory
        context = self._build_stateful_context(
            state=state,
            is_followup=should_followup,
            followup_topic=followup_topic,
        )

        # Add reasoning to scratchpad
        reasoning = self._generate_reasoning(state, should_followup, followup_topic)
        state = self.state_manager.add_reasoning(state, reasoning)

        logger.info(f"Agent reasoning: {reasoning}")

        # Generate question with LLM
        question = await self._generate_question_with_memory(
            context=context,
            state=state,
            is_followup=should_followup,
            followup_topic=followup_topic,
        )

        if question:
            # Update state
            state = self.state_manager.add_question(state, question.model_dump())

            # Mark topic as explored
            if followup_topic:
                state = self.state_manager.mark_topic_explored(state, followup_topic)

        return question, state

    async def process_answer_and_extract_insights(
        self,
        state: InterviewState,
        answer: str,
    ) -> InterviewState:
        """
        Process candidate answer and extract insights for memory
        
        Args:
            state: Current interview state
            answer: Candidate's answer text
            
        Returns:
            Updated state with insights
        """
        # Extract insights using LLM
        insights = await self._extract_insights_from_answer(
            answer=answer,
            question=state.questions[-1] if state.questions else None,
            interview_type=state.interview_type,
        )

        # Add answer with insights to state
        state = self.state_manager.add_answer(state, answer, insights)

        # Log insights
        for insight in insights:
            logger.info(
                f"Extracted insight: {insight.topic} - {insight.statement} "
                f"[{insight.confidence_level}, follow_up={insight.follow_up_potential}]"
            )

        return state

    def _build_stateful_context(
        self,
        state: InterviewState,
        is_followup: bool,
        followup_topic: Optional[str],
    ) -> str:
        """Build context with memory and reasoning"""
        lines = []

        # Header
        lines.append("=== STATEFUL INTERVIEW CONTEXT ===")
        lines.append(f"Question {state.current_question_number + 1}/{state.max_questions}")
        lines.append(f"Interview Type: {state.interview_type}")
        lines.append(f"Difficulty: {state.difficulty}")
        lines.append("")

        # Candidate info
        lines.append("=== CANDIDATE PROFILE ===")
        if state.candidate_name:
            lines.append(f"Name: {state.candidate_name}")
        if state.candidate_skills:
            lines.append(f"Skills: {', '.join(state.candidate_skills[:10])}")
        lines.append("")

        # Job description
        if state.job_description:
            lines.append("=== JOB REQUIREMENTS ===")
            lines.append(state.job_description[:500])
            lines.append("")

        # MEMORY - Topics covered
        if state.memory.covered_topics:
            lines.append("=== TOPICS ALREADY COVERED ===")
            lines.append(", ".join(state.memory.covered_topics))
            lines.append("")

        # MEMORY - Key insights
        if state.memory.candidate_insights:
            lines.append("=== KEY INSIGHTS FROM PREVIOUS ANSWERS ===")
            recent_insights = state.memory.candidate_insights[-5:]
            for insight in recent_insights:
                lines.append(
                    f"- {insight.topic}: \"{insight.statement}\" "
                    f"[Confidence: {insight.confidence_level}]"
                )
            lines.append("")

        # MEMORY - Topics to explore
        if state.memory.topics_to_explore:
            lines.append("=== TOPICS TO EXPLORE (Priority) ===")
            lines.append(", ".join(state.memory.topics_to_explore[:5]))
            lines.append("")

        # MEMORY - Agent reasoning
        if state.memory.reasoning_history:
            lines.append("=== AGENT REASONING HISTORY (Scratchpad) ===")
            recent_reasoning = state.memory.reasoning_history[-3:]
            for r in recent_reasoning:
                lines.append(f"- {r}")
            lines.append("")

        # Recent conversation
        if state.conversation:
            lines.append("=== RECENT CONVERSATION ===")
            recent = state.conversation[-4:]  # Last 2 Q&A pairs
            for msg in recent:
                speaker = "INTERVIEWER" if msg["speaker"] == "ai" else "CANDIDATE"
                text = msg["text"][:150] + "..." if len(msg["text"]) > 150 else msg["text"]
                lines.append(f"{speaker}: {text}")
            lines.append("")

        # Task instructions
        lines.append("=== TASK ===")
        
        if is_followup and followup_topic:
            lines.append(f"IMPORTANT: Generate a FOLLOW-UP question about: {followup_topic}")
            lines.append("The candidate mentioned this topic in their previous answer.")
            lines.append("Dig deeper into their experience, ask for specific examples, or probe further.")
        elif state.current_question_number == 0:
            lines.append("Generate a warm opening question that:")
            lines.append("- Puts the candidate at ease")
            lines.append("- Relates to their background")
        elif state.current_question_number + 1 == state.max_questions:
            lines.append("Generate a closing question that:")
            lines.append("- Wraps up naturally")
            lines.append("- Lets candidate highlight strengths")
        else:
            lines.append("Generate the next question that:")
            lines.append("- Builds on previous answers")
            lines.append("- Does NOT repeat covered topics")
            lines.append("- Explores new aspects or follows up on interesting points")

        return "\n".join(lines)

    def _generate_reasoning(
        self,
        state: InterviewState,
        should_followup: bool,
        followup_topic: Optional[str],
    ) -> str:
        """Generate agent's reasoning for scratchpad"""
        q_num = state.current_question_number + 1

        if should_followup and followup_topic:
            return (
                f"Q{q_num} Decision: Follow-up on '{followup_topic}' "
                f"from previous answer. Candidate showed interest/weakness here."
            )
        elif q_num == 1:
            return f"Q{q_num} Decision: Opening question to establish rapport and baseline."
        elif q_num == state.max_questions:
            return f"Q{q_num} Decision: Closing question to wrap up and let candidate shine."
        else:
            covered = ", ".join(state.memory.covered_topics[-3:]) if state.memory.covered_topics else "none"
            return (
                f"Q{q_num} Decision: Continue interview. "
                f"Already covered: {covered}. Exploring new territory."
            )

    async def _generate_question_with_memory(
        self,
        context: str,
        state: InterviewState,
        is_followup: bool,
        followup_topic: Optional[str],
    ) -> Optional[Question]:
        """Generate question using LLM with full memory context"""
        
        system_prompt = """You are an expert interviewer with memory of the entire conversation.

Generate ONE interview question based on the context provided.
Pay special attention to:
- Topics already covered (avoid repetition)
- Key insights from previous answers (follow up on interesting points)
- Agent reasoning history (understand the interview flow)

Return ONLY valid JSON:
{
  "question_text": "Your question here",
  "category": "technical|behavioral|hr",
  "difficulty": "easy|medium|hard",
  "expected_topics": ["topic1", "topic2"],
  "is_followup": true|false,
  "followup_topic": "topic" or null
}"""

        question_data = await self.groq.generate_structured_response(
            system_prompt=system_prompt,
            user_prompt=context,
            expected_fields=["question_text", "category", "difficulty"],
            temperature=0.8,
            max_tokens=400,
        )

        if not question_data:
            # Fallback
            return self._generate_fallback_question(state, is_followup, followup_topic)

        try:
            question = Question(
                question_text=question_data["question_text"],
                category=question_data["category"],
                difficulty=question_data["difficulty"],
                expected_topics=question_data.get("expected_topics", []),
            )
            return question
        except Exception as e:
            logger.error(f"Failed to create Question: {e}")
            return self._generate_fallback_question(state, is_followup, followup_topic)

    async def _extract_insights_from_answer(
        self,
        answer: str,
        question: Optional[Dict[str, Any]],
        interview_type: str,
    ) -> List[CandidateInsight]:
        """Extract insights from candidate answer using LLM"""
        
        if not question:
            return []

        system_prompt = """You are an expert at analyzing interview answers.

Extract key insights that could lead to follow-up questions.

Return ONLY valid JSON array:
[
  {
    "topic": "specific topic mentioned",
    "statement": "what the candidate said about it",
    "confidence_level": "strong|weak|unclear",
    "follow_up_potential": true|false
  }
]

Extract 1-3 insights maximum. Focus on:
- Technical skills mentioned
- Experience gaps or uncertainties
- Interesting points worth exploring
- Red flags or areas of weakness"""

        context = f"""Question: {question.get('question_text', 'N/A')}

Candidate's Answer:
{answer}"""

        insights_data = await self.groq.generate_structured_response(
            system_prompt=system_prompt,
            user_prompt=context,
            expected_fields=[],  # Array response
            temperature=0.3,
            max_tokens=400,
        )

        if not insights_data:
            return []

        # Handle array response
        insights_list = insights_data if isinstance(insights_data, list) else [insights_data]

        insights = []
        for item in insights_list:
            try:
                insight = CandidateInsight(
                    topic=item.get("topic", "general"),
                    statement=item.get("statement", ""),
                    confidence_level=item.get("confidence_level", "unclear"),
                    follow_up_potential=item.get("follow_up_potential", False),
                )
                insights.append(insight)
            except Exception as e:
                logger.warning(f"Failed to parse insight: {e}")

        return insights

    def _generate_fallback_question(
        self,
        state: InterviewState,
        is_followup: bool,
        followup_topic: Optional[str],
    ) -> Question:
        """Generate fallback question when LLM fails"""
        
        q_num = state.current_question_number + 1

        if is_followup and followup_topic:
            question_text = f"Can you tell me more about your experience with {followup_topic}?"
        elif q_num == 1:
            question_text = "Can you start by telling me about your background and experience?"
        elif q_num == state.max_questions:
            question_text = "Is there anything else you'd like to share that we haven't covered?"
        else:
            skills = state.candidate_skills
            if skills and len(skills) >= q_num:
                question_text = f"Tell me about your experience with {skills[q_num - 1]}."
            else:
                question_text = "What projects are you most proud of in your career?"

        return Question(
            question_text=question_text,
            category=state.interview_type,
            difficulty=state.difficulty,
            expected_topics=[followup_topic] if followup_topic else [],
        )