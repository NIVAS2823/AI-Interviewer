"""
Interview Engine Service (Fully Integrated with Stateful Agent)
Now with memory, intelligent follow-ups, and agent scratchpad
"""
from typing import Optional
import logging

from app.models.interview import InterviewModel, Question, Evaluation
from app.services.evaluation_service import EvaluationService
from app.utils.videosdk_agent import VideoSDKAgentService
from app.services.repositories.repository_factory import get_repositories
from app.services.domain.response_service import ResponseService
from app.services.domain.conversation_service import ConversationService
from app.services.domain.context_builder import QuestionContextBuilder
from app.services.orchestration.stateful_question_agent import StatefulQuestionAgent
from app.services.orchestration.interview_state import InterviewState

logger = logging.getLogger(__name__)


class InterviewEngineService:
    """
    Core interview orchestrator with stateful AI agent
    
    NEW FEATURES:
    ✅ Remembers previous answers
    ✅ Generates intelligent follow-ups
    ✅ Maintains agent scratchpad
    ✅ Extracts insights from answers
    ✅ Avoids duplicate questions
    """

    def __init__(self):
        # External integrations
        self.videosdk = VideoSDKAgentService()
        self.evaluation_service = EvaluationService()
        
        # Domain services
        self.response_service = ResponseService()
        self.conversation_service = ConversationService()
        self.context_builder = QuestionContextBuilder()
        
        # ✅ NEW: Stateful agent with memory
        self.stateful_agent = StatefulQuestionAgent()

    async def create_interview(
        self,
        candidate_id: str,
        resume_id: str,
        interview_type: str,
        difficulty: str,
        max_questions: int,
        db,
        job_description: Optional[str] = None,
    ) -> InterviewModel:
        """Create new interview session with VideoSDK AI agent"""
        repos = get_repositories(db)

        # Validate resume
        parsed_resume = await repos.resumes.get_parsed_data(resume_id)
        if not parsed_resume:
            raise ValueError("Resume not found or not yet parsed")

        # Create VideoSDK meeting and agent
        meeting_id = await self.videosdk.create_meeting()
        meeting_token = None
        agent_id = None

        if meeting_id:
            meeting_token = await self.videosdk.get_meeting_token(meeting_id)

            # Build candidate context
            candidate_info = self.context_builder.build_candidate_info_dict(parsed_resume)

            # Create system prompt
            system_prompt = self.videosdk.build_system_prompt(
                interviewer_name="Sarah",
                interview_type=interview_type,
                questions=[],
                candidate_info=candidate_info,
            )

            # Create AI agent
            agent_id = await self.videosdk.create_ai_agent(
                meeting_id=meeting_id,
                interviewer_name="Sarah",
                questions=[],
                system_prompt=system_prompt,
                voice="en-US-Neural2-F",
            )

            if agent_id:
                logger.info(f"✅ VideoSDK AI Agent created: {agent_id}")
            else:
                logger.warning("⚠️ Agent creation failed")

        # Create interview record
        interview_id = await repos.interviews.create_interview(
            candidate_id=candidate_id,
            resume_id=resume_id,
            interview_type=interview_type,
            difficulty=difficulty,
            max_questions=max_questions,
            session_id=meeting_id,
            meeting_token=meeting_token,
            agent_id=agent_id,
            job_description=job_description,
        )

        if not interview_id:
            raise RuntimeError("Failed to create interview record")

        # ✅ NEW: Create initial agent state
        initial_state = await repos.interview_state.create_initial_state_from_interview(interview_id)
        
        if initial_state:
            await repos.interview_state.save_state(initial_state)
            logger.info(f"✅ Initial agent state created for {interview_id}")
        else:
            logger.warning(f"⚠️ Failed to create initial state for {interview_id}")

        logger.info(f"✅ Interview created: {interview_id}")

        interview = await repos.interviews.get_interview(interview_id)
        if not interview:
            raise RuntimeError("Failed to fetch created interview")

        return interview

    async def start_interview(self, interview_id: str, db) -> InterviewModel:
        """Start interview session and activate AI agent"""
        repos = get_repositories(db)

        logger.info(f"[START_INTERVIEW] Starting interview {interview_id}")

        interview = await repos.interviews.get_interview(interview_id)
        if not interview:
            raise ValueError("Interview not found")

        # ✅ NEW: Ensure agent state exists
        state = await self._get_or_create_state(interview_id, repos)

        # Generate first question using stateful agent
        question_count = await repos.interviews.get_question_count(interview_id)
        
        if question_count == 0:
            logger.info(f"[START_INTERVIEW] Generating first question with stateful agent")
            
            first_question = await self._generate_next_question_stateful(interview_id, db)
            
            if first_question:
                logger.info(f"[START_INTERVIEW] Q1 generated: {first_question.question_text[:80]}")

        # Start VideoSDK agent
        if interview.agent_id and interview.session_id:
            try:
                await self.videosdk.start_agent(
                    meeting_id=interview.session_id,
                    agent_id=interview.agent_id
                )
                logger.info(f"[START_INTERVIEW] Agent started")
            except Exception as e:
                logger.error(f"[START_INTERVIEW] Failed to start agent: {e}")

        # Mark as in_progress
        updated_interview = await repos.interviews.start_interview(interview_id)
        
        if not updated_interview:
            raise RuntimeError("Database failed to update interview")

        logger.info(f"[START_INTERVIEW] Interview {interview_id} is now in_progress")

        return updated_interview

    async def end_interview(self, interview_id: str, db) -> InterviewModel:
        """End interview, stop agent, and evaluate candidate"""
        repos = get_repositories(db)

        logger.info(f"🏁 Ending interview {interview_id}")

        interview = await repos.interviews.get_interview(interview_id)
        if not interview:
            raise ValueError("Interview not found")

        # Stop VideoSDK agent and meeting
        if interview.agent_id:
            try:
                await self.videosdk.stop_agent(interview.agent_id)
                logger.info(f"✅ AI Agent stopped")
            except Exception as e:
                logger.warning(f"⚠️ Failed to stop agent: {e}")

        if interview.session_id:
            try:
                await self.videosdk.end_meeting(interview.session_id)
                logger.info(f"✅ Meeting ended")
            except Exception as e:
                logger.warning(f"⚠️ Failed to end meeting: {e}")

        # Get conversation and evaluate
        conversation = await repos.conversations.get_conversation(interview_id)
        candidate_messages = [m for m in conversation if m.speaker == "candidate"]

        logger.info(f"📊 Total messages: {len(conversation)}, Candidate: {len(candidate_messages)}")

        # ✅ NEW: Log final agent memory state
        state = await repos.interview_state.load_state(interview_id)
        if state:
            logger.info(f"🧠 Final Agent Memory:")
            logger.info(f"   - Topics covered: {state.memory.covered_topics}")
            logger.info(f"   - Insights extracted: {len(state.memory.candidate_insights)}")
            logger.info(f"   - Reasoning steps: {len(state.memory.reasoning_history)}")

        evaluation = None

        if len(candidate_messages) == 0:
            logger.warning("⚠️ Zero candidate responses")
            
            evaluation = Evaluation(
                skipped_interview=True,
                scores={
                    "overall_score": 0,
                    "technical_score": 0,
                    "communication_score": 0,
                    "confidence_score": 0,
                    "behavioral_score": 0,
                },
                sentiment={"positive": 0.0, "neutral": 1.0, "negative": 0.0},
                strengths=[],
                improvements=["Candidate did not answer any questions."],
                detailed_feedback="Interview ended without any candidate responses.",
                question_scores=[],
            )
        else:
            try:
                questions = await repos.interviews.get_questions(interview_id)
                
                logger.info("🤖 Running AI evaluation...")
                
                evaluation = await self.evaluation_service.evaluate_interview(
                    conversation=conversation,
                    questions=questions,
                    interview_type=interview.interview_type,
                    difficulty=interview.difficulty,
                )
                
                logger.info("✅ AI evaluation completed")
            except Exception as e:
                logger.error(f"❌ Evaluation failed: {e}")

        # Mark as completed
        updated_interview = await repos.interviews.end_interview(
            interview_id=interview_id,
            evaluation=evaluation
        )

        if not updated_interview:
            raise RuntimeError("Failed to update interview as completed")

        logger.info(f"✅ Interview {interview_id} completed")

        return updated_interview

    async def add_message(
        self,
        interview_id: str,
        speaker: str,
        text: str,
        db,
    ) -> bool:
        """
        Add message to conversation
        ✅ NEW: Also processes answer through stateful agent if it's a candidate message
        """
        repos = get_repositories(db)
        
        # Add message to conversation
        success = await repos.conversations.add_message(interview_id, speaker, text)
        
        if not success:
            return False

        # ✅ NEW: If candidate message, process through stateful agent
        if speaker == "candidate":
            try:
                state = await self._get_or_create_state(interview_id, repos)
                
                if state:
                    # Extract insights from answer
                    updated_state = await self.stateful_agent.process_answer_and_extract_insights(
                        state=state,
                        answer=text,
                    )
                    
                    # Save updated state
                    await repos.interview_state.save_state(updated_state)
                    
                    logger.info(f"🧠 Processed candidate answer, extracted {len(updated_state.memory.candidate_insights) - len(state.memory.candidate_insights)} new insights")
            except Exception as e:
                logger.error(f"Failed to process answer through stateful agent: {e}")
        
        return True

    async def generate_next_question(self, interview_id: str, db) -> Optional[Question]:
        """
        ✅ UPDATED: Generate next question using stateful agent with memory
        This is the main entry point that now uses intelligent follow-ups
        """
        return await self._generate_next_question_stateful(interview_id, db)

    async def _generate_next_question_stateful(
        self, 
        interview_id: str, 
        db
    ) -> Optional[Question]:
        """
        ✅ NEW: Generate question using stateful agent with full memory
        """
        repos = get_repositories(db)

        # Get or create state
        state = await self._get_or_create_state(interview_id, repos)
        
        if not state:
            logger.error(f"Failed to get state for interview {interview_id}")
            return None

        # Check if max questions reached
        if state.current_question_number >= state.max_questions:
            logger.info(f"Max questions ({state.max_questions}) reached")
            return None

        # ✅ Generate using stateful agent (with memory and follow-ups)
        logger.info(f"🧠 Generating question with stateful agent (turn {state.memory.turn_count})")
        
        question, updated_state = await self.stateful_agent.generate_next_question_stateful(state)

        if not question:
            logger.error("Stateful agent failed to generate question")
            return None

        # Save question to database
        success = await repos.interviews.add_question(interview_id, question)
        
        if not success:
            logger.error("Failed to save question to database")
            return None

        # ✅ Save updated state (with new reasoning)
        await repos.interview_state.save_state(updated_state)

        logger.info(f"✅ Generated question #{updated_state.current_question_number}")
        logger.info(f"   Agent reasoning: {updated_state.memory.reasoning_history[-1]}")
        
        return question

    async def generate_ai_reply(self, interview_id: str, candidate_text: str, db) -> str:
        """
        Generate AI interviewer reply to candidate's message
        ✅ UPDATED: Now processes answer through agent first
        """
        repos = get_repositories(db)

        interview = await repos.interviews.get_interview(interview_id)
        if not interview:
            raise ValueError("Interview not found")

        # ✅ NEW: Process answer through stateful agent first
        state = await repos.interview_state.load_state(interview_id)
        
        if state:
            updated_state = await self.stateful_agent.process_answer_and_extract_insights(
                state=state,
                answer=candidate_text,
            )
            await repos.interview_state.save_state(updated_state)

        current_count = await repos.interviews.get_question_count(interview_id)

        if current_count < interview.max_questions:
            # Generate next question (now stateful!)
            next_question = await self._generate_next_question_stateful(interview_id, db)

            if next_question:
                # Use ResponseService for acknowledgment
                return self.response_service.generate_question_response(
                    next_question=next_question,
                    include_acknowledgment=True
                )
            else:
                return self.response_service.generate_thinking_message()
        else:
            # All questions done
            return self.response_service.generate_completion_message(
                include_instruction=True
            )

    async def simulate_interview_conversation(self, interview_id: str, db) -> bool:
        """Simulate a complete interview conversation"""
        repos = get_repositories(db)

        interview = await repos.interviews.get_interview(interview_id)
        if not interview:
            raise ValueError("Interview not found")

        if interview.status != "in_progress":
            raise ValueError("Interview must be in progress to simulate")

        questions = await repos.interviews.get_questions(interview_id)

        if not questions:
            logger.warning("No questions found for simulation")
            return False

        # Try worker simulation first
        if interview.agent_id:
            transcript = await self._try_worker_simulation(interview.agent_id)
            
            if transcript:
                conversation = self._convert_transcript(transcript)
                success = await repos.conversations.replace_conversation(
                    interview_id, 
                    conversation
                )
                
                if success:
                    logger.info(f"✅ Simulated via worker")
                    return True

        # Fallback: Use ConversationService
        conversation = await self.conversation_service.simulate_full_conversation(questions)
        
        success = await repos.conversations.replace_conversation(interview_id, conversation)
        
        if success:
            logger.info(f"✅ Simulated {len(conversation)} messages")
        
        return success

    async def get_agent_memory_summary(self, interview_id: str, db) -> dict:
        """
        ✅ NEW: Get summary of agent's memory (for debugging/analytics)
        """
        repos = get_repositories(db)
        
        state = await repos.interview_state.load_state(interview_id)
        
        if not state:
            return {
                "available": False,
                "message": "No agent state found"
            }
        
        return {
            "available": True,
            "turn_count": state.memory.turn_count,
            "current_question": state.current_question_number,
            "max_questions": state.max_questions,
            "covered_topics": state.memory.covered_topics,
            "topics_to_explore": state.memory.topics_to_explore,
            "insights_extracted": len(state.memory.candidate_insights),
            "reasoning_steps": len(state.memory.reasoning_history),
            "recent_reasoning": state.memory.reasoning_history[-3:] if state.memory.reasoning_history else [],
            "recent_insights": [
                {
                    "topic": i.topic,
                    "confidence": i.confidence_level,
                    "follow_up": i.follow_up_potential
                }
                for i in state.memory.candidate_insights[-3:]
            ],
        }

    async def _get_or_create_state(
        self, 
        interview_id: str, 
        repos
    ) -> Optional[InterviewState]:
        """
        ✅ NEW: Get existing state or create new one
        """
        # Try to load existing state
        state = await repos.interview_state.load_state(interview_id)
        
        if state:
            return state
        
        # Create new state
        logger.info(f"Creating initial state for interview {interview_id}")
        
        state = await repos.interview_state.create_initial_state_from_interview(interview_id)
        
        if state:
            await repos.interview_state.save_state(state)
            logger.info(f"✅ Initial state created and saved")
        
        return state

    async def _try_worker_simulation(self, agent_id: str):
        """Try worker simulation"""
        try:
            import httpx
            from app.core.config import settings

            worker_url = settings.AGENT_WORKER_URL

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(f"{worker_url}/simulate/{agent_id}")

                if response.status_code == 200:
                    transcript_response = await client.get(f"{worker_url}/transcript/{agent_id}")

                    if transcript_response.status_code == 200:
                        return transcript_response.json()["transcript"]
        except Exception as e:
            logger.warning(f"Worker simulation failed: {e}")
        
        return None

    def _convert_transcript(self, transcript):
        """Convert worker transcript to conversation"""
        from datetime import datetime
        
        conversation = []
        for msg in transcript:
            conversation.append({
                "speaker": "ai" if msg["role"] == "assistant" else "candidate",
                "text": msg["content"],
                "timestamp": datetime.utcnow(),
            })
        return conversation