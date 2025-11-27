from typing import Dict, List, Optional
from bson import ObjectId
from datetime import datetime

from app.models.interview import InterviewModel, Question, ConversationMessage, Evaluation
from app.models.resume import ResumeModel, ParsedData
from app.services.question_generator import QuestionGeneratorService
from app.services.evaluation_service import EvaluationService
from app.utils.videosdk_agent import VideoSDKAgentService  # Updated import
from app.core.database import get_database


class InterviewEngineService:
    """Core interview engine with REAL VideoSDK AI agent integration"""

    def __init__(self):
        self.question_generator = QuestionGeneratorService()
        self.evaluation_service = EvaluationService()
        self.videosdk = VideoSDKAgentService()  # Enhanced VideoSDK

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
        """
        Create new interview session with REAL AI agent

        Steps:
        1. Fetch resume data
        2. Generate questions using Groq AI
        3. Create VideoSDK meeting
        4. Create AI agent with avatar, voice, STT/TTS
        5. Return meeting credentials for frontend
        """

        # Fetch resume
        resume_doc = await db.resumes.find_one({"_id": ObjectId(resume_id)})
        if not resume_doc:
            raise ValueError("Resume not found")

        parsed_data = resume_doc.get("parsed_data")
        if not parsed_data:
            raise ValueError("Resume not yet parsed")

        # Convert to ParsedData model
        parsed_resume = ParsedData(**parsed_data)

        # Generate questions using Groq AI (deferred; empty until generated)
        questions: List[Question] = []
        question_texts: List[str] = []

        # Create VideoSDK meeting
        meeting_id = await self.videosdk.create_meeting()
        meeting_token = None
        agent_id = None

        if meeting_id:
            # Generate meeting token for candidate
            meeting_token = await self.videosdk.get_meeting_token(meeting_id)

            # Build system prompt for AI agent (questions may be filled later)
            candidate_info = {
                "name": parsed_resume.name,
                "skills": parsed_resume.skills[:10] if parsed_resume.skills else [],
                "experience_years": len(parsed_resume.experience) if parsed_resume.experience else 0,
                "education": [
                    f"{edu.degree} in {edu.field}"
                    for edu in (parsed_resume.education[:2] if parsed_resume.education else [])
                ],
            }

            system_prompt = self.videosdk.build_system_prompt(
                interviewer_name="Sarah",
                interview_type=interview_type,
                questions=question_texts,
                candidate_info=candidate_info,
            )

            # Create AI Agent with avatar, voice, STT/TTS
            agent_id = await self.videosdk.create_ai_agent(
                meeting_id=meeting_id,
                interviewer_name="Sarah",
                questions=question_texts,
                system_prompt=system_prompt,
                voice="en-US-Neural2-F",
            )

            if agent_id:
                print(f"✅ REAL AI Agent created with avatar and voice!")
            else:
                print("⚠️ Agent creation failed - will use fallback mode")

        # Create interview document
        interview = InterviewModel(
            candidate_id=ObjectId(candidate_id),
            resume_id=ObjectId(resume_id),
            job_description=job_description,
            session_id=meeting_id,
            meeting_token=meeting_token,
            agent_id=agent_id,
            interview_type=interview_type,
            difficulty=difficulty,
            max_questions=max_questions,
            questions=questions,
            current_question_index=0,
            status="created",
        )

        # Save to database
        interview_dict = interview.model_dump(by_alias=True, exclude={"id"})
        result = await db.interviews.insert_one(interview_dict)
        interview.id = result.inserted_id

        print(f"✅ Interview created with REAL VideoSDK AI agent: {result.inserted_id}")

        return interview

    async def start_interview(self, interview_id: str, db) -> InterviewModel:
        """
        Start interview session and activate AI agent
        Also generates the first question if not already generated
        """
        import logging

        logger = logging.getLogger(__name__)

        interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
        if not interview:
            raise ValueError("Interview not found")

        # Generate first question if not already generated
        questions = interview.get("questions", [])
        if len(questions) == 0:
            logger.info(f"Generating first question for interview {interview_id}")

            # Generate first question
            first_question = await self.generate_next_question(interview_id, db)
            if first_question:
                logger.info(f"✅ First question generated: {first_question.question_text[:50]}...")

            # refresh interview after mutation
            interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})

        # Start the AI agent in the meeting (if present)
        agent_started = False
        if interview.get("agent_id") and interview.get("session_id"):
            agent_started = await self.videosdk.start_agent(
                meeting_id=interview["session_id"], agent_id=interview["agent_id"]
            )

            if agent_started:
                print(f"✅ AI Agent is NOW LIVE in meeting!")

        # Update status
        result = await db.interviews.find_one_and_update(
            {"_id": ObjectId(interview_id)},
            {
                "$set": {
                    "status": "in_progress",
                    "start_time": datetime.utcnow(),
                }
            },
            return_document=True,
        )

        return InterviewModel(**result)

    async def end_interview(self, interview_id: str, db) -> InterviewModel:
        """
        End interview session and trigger evaluation.
        Handles:
        - Normal evaluation
        - Zero-answer evaluation (prevents infinite 404 loop)
        """
        import logging
        logger = logging.getLogger(__name__)

        interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
        if not interview:
            raise ValueError("Interview not found")

        end_time = datetime.utcnow()
        duration_minutes = 0

        if interview.get("start_time"):
            duration = end_time - interview["start_time"]
            duration_minutes = int(duration.total_seconds() / 60)

        logger.info(f"🏁 Ending interview {interview_id}")

        # --- Stop AI Agent ---
        if interview.get("agent_id"):
            try:
                await self.videosdk.stop_agent(interview["agent_id"])
                logger.info(f"✅ AI Agent stopped: {interview['agent_id']}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to stop agent: {e}")

        # --- End VideoSDK Meeting ---
        if interview.get("session_id"):
            try:
                await self.videosdk.end_meeting(interview["session_id"])
                logger.info(f"✅ Meeting ended: {interview['session_id']}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to end meeting: {e}")

        # ----------------------------
        # FETCH EXISTING CONVERSATION
        # ----------------------------
        existing_conversation = interview.get("conversation", [])

        logger.info(f"📊 Messages in DB: {len(existing_conversation)}")

        ai_messages = [m for m in existing_conversation if m.get("speaker") == "ai"]
        candidate_messages = [m for m in existing_conversation if m.get("speaker") == "candidate"]

        logger.info(f"   AI msgs: {len(ai_messages)}")
        logger.info(f"   Candidate msgs: {len(candidate_messages)}")

        # ===============================================================
        # 🔥 ZERO-ANSWER CASE — PREVENT INFINITE 404 LOOP
        # ===============================================================
        if len(candidate_messages) == 0:
            logger.warning("⚠️ No candidate answers — creating ZERO evaluation immediately")

            zero_eval = {
                "skipped_interview": True,  # <-- NEW FLAG
                "scores": {
                    "overall_score": 0,
                    "technical_score": 0,
                    "communication_score": 0,
                    "confidence_score": 0,
                    "behavioral_score": 0,
                },
                "sentiment": {
                    "positive": 0.0,
                    "neutral": 1.0,
                    "negative": 0.0,
                },
                "strengths": [],
                "improvements": ["Candidate did not answer any questions."],
                "detailed_feedback": "Interview ended without any candidate responses.",
                "question_scores": [],
            }

            await db.interviews.update_one(
                {"_id": ObjectId(interview_id)},
                {
                    "$set": {
                        "evaluation": zero_eval,
                        "status": "completed",
                        "end_time": end_time,
                        "duration_minutes": duration_minutes,
                        "updated_at": datetime.utcnow(),
                    }
                }
            )

            logger.info("✅ Zero-answer evaluation stored successfully")

            # Reload interview
            interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
            return InterviewModel(**interview)

        # ===============================================================
        # NORMAL EVALUATION (IF USER ANSWERED AT LEAST 1 QUESTION)
        # ===============================================================
        evaluation = None
        try:
            logger.info("🤖 Running AI evaluation...")

            conversation = [ConversationMessage(**msg) for msg in existing_conversation]
            questions = [Question(**q) for q in interview.get("questions", [])]

            evaluation = await self.evaluation_service.evaluate_interview(
                conversation=conversation,
                questions=questions,
                interview_type=interview.get("interview_type", "mixed"),
                difficulty=interview.get("difficulty", "medium"),
            )

            logger.info("✅ AI evaluation finished.")

        except Exception as e:
            logger.error(f"❌ Evaluation failed: {e}")

        # --- Prepare update data ---
        update_data = {
            "status": "completed",
            "end_time": end_time,
            "duration_minutes": duration_minutes,
            "updated_at": datetime.utcnow(),
        }

        if evaluation:
            update_data["evaluation"] = evaluation.model_dump()

        updated = await db.interviews.find_one_and_update(
            {"_id": ObjectId(interview_id)},
            {"$set": update_data},
            return_document=True,
        )

        logger.info(f"✅ Interview {interview_id} completed and saved")
        return InterviewModel(**updated)

    async def add_message(
        self,
        interview_id: str,
        speaker: str,
        text: str,
        db,
    ) -> bool:
        """
        Add message to conversation (for manual logging if needed)
        """
        message = ConversationMessage(speaker=speaker, text=text, timestamp=datetime.utcnow())

        result = await db.interviews.update_one(
            {"_id": ObjectId(interview_id)},
            {"$push": {"conversation": message.model_dump()}, "$set": {"updated_at": datetime.utcnow()}},
        )

        return result.modified_count > 0

    async def simulate_interview_conversation(self, interview_id: str, db) -> bool:
        """
        Simulate a complete interview conversation using Groq AI.
        Fallback when VideoSDK agent is not available.
        """
        import logging

        logger = logging.getLogger(__name__)

        interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
        if not interview:
            raise ValueError("Interview not found")

        if interview.get("status") != "in_progress":
            raise ValueError("Interview must be in progress to simulate")

        questions = [Question(**q) for q in interview.get("questions", [])]

        if not questions:
            logger.warning("No questions found for interview simulation")
            return False

        # ---------- Try worker simulation ----------
        agent_id = interview.get("agent_id")
        if agent_id:
            try:
                import httpx
                from app.core.config import settings

                worker_url = settings.AGENT_WORKER_URL

                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(f"{worker_url}/simulate/{agent_id}")

                    if response.status_code == 200:
                        transcript_response = await client.get(f"{worker_url}/transcript/{agent_id}")

                        if transcript_response.status_code == 200:
                            transcript = transcript_response.json()["transcript"]

                            conversation = []
                            for msg in transcript:
                                conversation.append(
                                    {
                                        "speaker": "ai" if msg["role"] == "assistant" else "candidate",
                                        "text": msg["content"],
                                        "timestamp": datetime.utcnow(),
                                    }
                                )

                            await db.interviews.update_one(
                                {"_id": ObjectId(interview_id)},
                                {"$set": {"conversation": conversation, "updated_at": datetime.utcnow()}},
                            )

                            logger.info(f"✅ Simulated {len(conversation)} messages via worker")
                            return True

            except Exception as e:
                logger.warning(f"Worker simulation failed: {e}, using fallback")

        # ---------- Fallback Groq-only simulation ----------
        conversation = []

        # AI greeting
        conversation.append({"speaker": "ai", "text": "Hello! I'm your AI interviewer. Let's begin.", "timestamp": datetime.utcnow()})

        # Loop through each question
        for question in questions:
            # Ask question
            conversation.append({"speaker": "ai", "text": question.question_text, "timestamp": datetime.utcnow()})

            # Generate answer
            candidate_answer = await self._generate_simulated_answer(question.question_text, question.category)

            conversation.append({"speaker": "candidate", "text": candidate_answer, "timestamp": datetime.utcnow()})

            # Acknowledgment
            conversation.append({"speaker": "ai", "text": "Thanks for the answer.", "timestamp": datetime.utcnow()})

        # End message
        conversation.append({"speaker": "ai", "text": "That concludes our interview. Thank you!", "timestamp": datetime.utcnow()})

        # Save
        await db.interviews.update_one(
            {"_id": ObjectId(interview_id)},
            {"$set": {"conversation": conversation, "updated_at": datetime.utcnow()}},
        )

        logger.info(f"✅ Simulated {len(conversation)} messages via fallback")
        return True

    async def _generate_simulated_answer(self, question: str, category: str) -> str:
        """Generate a simulated candidate answer using Groq AI."""
        from app.core.config import settings

        if not settings.GROQ_API_KEY:
            return (
                "Based on my experience, I would analyze the requirements "
                "and implement a clear, maintainable solution."
            )

        try:
            from groq import Groq

            client = Groq(api_key=settings.GROQ_API_KEY)

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a job candidate. Give a polished, professional "
                            f"2–3 sentence answer to a {category} interview question."
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                temperature=0.7,
                max_tokens=200,
            )

            return response.choices[0].message.content

        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to generate answer: {e}")
            return (
                "I would approach this by breaking down the requirements and applying "
                "best practices to deliver an effective solution."
            )

    async def generate_ai_reply(self, interview_id: str, candidate_text: str, db) -> str:
        """
        Generate AI interviewer reply to candidate's message
        Now with DYNAMIC question generation!
        """
        import logging
        from app.core.config import settings

        logger = logging.getLogger(__name__)

        interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
        if not interview:
            raise ValueError("Interview not found")

        # Get current state
        conversation = interview.get("conversation", [])
        questions = interview.get("questions", [])
        max_questions = interview.get("max_questions", 5)
        current_count = len(questions)

        # Check if we need to generate next question
        if current_count < max_questions:
            # Generate next question dynamically
            next_question = await self.generate_next_question(interview_id, db)

            if next_question:
                # Acknowledge answer and ask next question
                acknowledgments = [
                    "Thank you for that insight.",
                    "I appreciate your detailed answer.",
                    "That's helpful to know.",
                    "Interesting perspective.",
                    "I see, thank you for explaining.",
                ]

                import random

                ack = random.choice(acknowledgments)

                return f"{ack} {next_question.question_text}"
            else:
                # Failed to generate question
                return "Thank you for your answer. Let me think of the next question..."
        else:
            # All questions done
            return "Thank you for your detailed answers throughout this interview. That concludes our conversation today. Click 'End Interview' to see your evaluation results."

    async def generate_next_question(self, interview_id: str, db) -> Optional[Question]:
        """
        Generate the next interview question based on:
        - Resume
        - Job description
        - Previous Q&A
        - Interview type and difficulty
        """
        import logging
        from app.core.config import settings

        logger = logging.getLogger(__name__)

        interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
        if not interview:
            raise ValueError("Interview not found")

        # Check if we've reached max questions
        current_count = len(interview.get("questions", []))
        max_questions = interview.get("max_questions", 5)

        if current_count >= max_questions:
            logger.info(f"Max questions ({max_questions}) reached for interview {interview_id}")
            return None

        # Get resume
        resume_doc = await db.resumes.find_one({"_id": interview["resume_id"]})
        if not resume_doc or not resume_doc.get("parsed_data"):
            logger.error("Resume data not found")
            return None

        parsed_resume = ParsedData(**resume_doc["parsed_data"])

        # Get conversation history
        conversation = interview.get("conversation", [])
        job_description = interview.get("job_description", "")
        interview_type = interview.get("interview_type", "mixed")
        difficulty = interview.get("difficulty", "medium")

        # Build context
        context = self._build_dynamic_question_context(
            parsed_resume=parsed_resume,
            job_description=job_description,
            conversation=conversation,
            interview_type=interview_type,
            difficulty=difficulty,
            question_number=current_count + 1,
            total_questions=max_questions,
        )

        # Generate question using Groq
        if not settings.GROQ_API_KEY:
            # Fallback question
            return Question(
                question_text=f"Tell me more about your experience with the skills mentioned in your resume.",
                category=interview_type,
                difficulty=difficulty,
                expected_topics=parsed_resume.skills[:3] if parsed_resume.skills else [],
            )

        try:
            from groq import Groq

            client = Groq(api_key=settings.GROQ_API_KEY)

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert technical interviewer. Generate ONE interview question based on the context provided. 

Return ONLY valid JSON (no markdown, no extra text):
{
  "question_text": "Your question here",
  "category": "technical|behavioral|hr",
  "difficulty": "easy|medium|hard",
  "expected_topics": ["topic1", "topic2"]
}""",
                    },
                    {"role": "user", "content": context},
                ],
                temperature=0.8,
                max_tokens=300,
            )

            response_text = response.choices[0].message.content.strip()

            # Clean JSON
            if response_text.startswith("json"):
                response_text = response_text[7:]
            if response_text.startswith(""): 
                response_text = response_text[3:] 
            if response_text.endswith(""):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            import json

            data = json.loads(response_text)

            question = Question(
                question_text=data.get("question_text", ""),
                category=data.get("category", interview_type),
                difficulty=data.get("difficulty", difficulty),
                expected_topics=data.get("expected_topics", []),
            )

            # Save question to interview
            await db.interviews.update_one(
                {"_id": ObjectId(interview_id)},
                {"$push": {"questions": question.model_dump()}, "$set": {"updated_at": datetime.utcnow()}},
            )

            logger.info(f"✅ Generated dynamic question #{current_count + 1} for interview {interview_id}")
            return question

        except Exception as e:
            logger.error(f"Failed to generate dynamic question: {e}")

            # Fallback
            fallback_question = Question(
                question_text=f"Can you elaborate on your experience mentioned in your resume?",
                category=interview_type,
                difficulty=difficulty,
                expected_topics=[],
            )

            await db.interviews.update_one(
                {"_id": ObjectId(interview_id)},
                {"$push": {"questions": fallback_question.model_dump()}, "$set": {"updated_at": datetime.utcnow()}},
            )

            return fallback_question

    def _build_dynamic_question_context(
        self,
        parsed_resume: ParsedData,
        job_description: str,
        conversation: List[Dict],
        interview_type: str,
        difficulty: str,
        question_number: int,
        total_questions: int,
    ) -> str:
        """Build context for dynamic question generation"""

        context_parts: List[str] = []

        context_parts.append(f"=== INTERVIEW CONTEXT ===")
        context_parts.append(f"Question {question_number} of {total_questions}")
        context_parts.append(f"Interview Type: {interview_type}")
        context_parts.append(f"Difficulty: {difficulty}")
        context_parts.append("")

        # Resume info
        context_parts.append("=== CANDIDATE RESUME ===")
        if parsed_resume.name:
            context_parts.append(f"Name: {parsed_resume.name}")
        if parsed_resume.skills:
            context_parts.append(f"Skills: {', '.join(parsed_resume.skills[:10])}")
        if parsed_resume.experience:
            context_parts.append("Experience:")
            for exp in parsed_resume.experience[:3]:
                context_parts.append(f"  - {exp.role} at {exp.company}")
        context_parts.append("")

        # Job description
        if job_description:
            context_parts.append("=== JOB DESCRIPTION ===")
            context_parts.append(job_description[:500])  # Limit length
            context_parts.append("")

        # Previous Q&A
        if conversation:
            context_parts.append("=== PREVIOUS CONVERSATION ===")
            # Get last 4 exchanges (AI question + candidate answer)
            recent_conv = conversation[-(min(8, len(conversation))):]
            for msg in recent_conv:
                speaker = "INTERVIEWER" if msg["speaker"] == "ai" else "CANDIDATE"
                context_parts.append(f"{speaker}: {msg['text']}")
            context_parts.append("")

        # Instructions
        context_parts.append("=== TASK ===")
        if question_number == 1:
            context_parts.append("Generate a warm opening question that:")
            context_parts.append("- Puts the candidate at ease")
            context_parts.append("- Relates to their background")
            if job_description:
                context_parts.append("- Connects to the job requirements")
        elif question_number == total_questions:
            context_parts.append("Generate a closing question that:")
            context_parts.append("- Wraps up the interview naturally")
            context_parts.append("- Gives candidate chance to highlight strengths")
            context_parts.append("- Shows their motivation")
        else:
            context_parts.append("Generate the next question that:")
            context_parts.append("- Builds on the candidate's previous answers")
            context_parts.append("- Explores topics they mentioned")
            if job_description:
                context_parts.append("- Assesses fit for the job requirements")
            context_parts.append("- Is appropriate for the difficulty level")

        return "\n".join(context_parts)
