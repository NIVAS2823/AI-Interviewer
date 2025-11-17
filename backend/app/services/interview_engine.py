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
        db
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
        
        # Generate questions using Groq AI (FREE)
        questions = await self.question_generator.generate_questions(
            parsed_resume=parsed_resume,
            interview_type=interview_type,
            difficulty=difficulty,
            max_questions=max_questions
        )
        
        # Extract question texts for agent
        question_texts = [q.question_text for q in questions]
        
        # Create VideoSDK meeting
        meeting_id = await self.videosdk.create_meeting()
        meeting_token = None
        agent_id = None
        
        if meeting_id:
            # Generate meeting token for candidate
            meeting_token = await self.videosdk.get_meeting_token(meeting_id)
            
            # Build system prompt for AI agent
            candidate_info = {
                "name": parsed_resume.name,
                "skills": parsed_resume.skills[:10] if parsed_resume.skills else [],
                "experience_years": len(parsed_resume.experience) if parsed_resume.experience else 0,
                "education": [
                    f"{edu.degree} in {edu.field}" 
                    for edu in (parsed_resume.education[:2] if parsed_resume.education else [])
                ]
            }
            
            system_prompt = self.videosdk.build_system_prompt(
                interviewer_name="Sarah",
                interview_type=interview_type,
                questions=question_texts,
                candidate_info=candidate_info
            )
            
            # Create AI Agent with avatar, voice, STT/TTS
            agent_id = await self.videosdk.create_ai_agent(
                meeting_id=meeting_id,
                interviewer_name="Sarah",
                questions=question_texts,
                system_prompt=system_prompt,
                voice_id="en-US-Neural2-F"  # Female professional voice
            )
            
            if agent_id:
                print(f"✅ REAL AI Agent created with avatar and voice!")
            else:
                print("⚠️ Agent creation failed - will use fallback mode")
        
        # Create interview document
        interview = InterviewModel(
            candidate_id=ObjectId(candidate_id),
            resume_id=ObjectId(resume_id),
            session_id=meeting_id,
            meeting_token=meeting_token,
            agent_id=agent_id,
            interview_type=interview_type,
            difficulty=difficulty,
            max_questions=max_questions,
            questions=questions,
            current_question_index=0,
            status="created"
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
        """
        interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
        if not interview:
            raise ValueError("Interview not found")
        
        # Start the AI agent in the meeting
        if interview.get("agent_id") and interview.get("session_id"):
            agent_started = await self.videosdk.start_agent(
                meeting_id=interview["session_id"],
                agent_id=interview["agent_id"]
            )
            
            if agent_started:
                print(f"✅ AI Agent is NOW LIVE in meeting!")
        
        # Update status
        result = await db.interviews.find_one_and_update(
            {"_id": ObjectId(interview_id)},
            {
                "$set": {
                    "status": "in_progress",
                    "start_time": datetime.utcnow()
                }
            },
            return_document=True
        )
        
        return InterviewModel(**result)
    
    async def end_interview(self, interview_id: str, db) -> InterviewModel:
        """
        End interview session and trigger evaluation
        
        Steps:
        1. Stop AI agent
        2. Get transcript from VideoSDK
        3. End meeting
        4. Trigger AI evaluation
        5. Store results
        """
        interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
        if not interview:
            raise ValueError("Interview not found")
        
        end_time = datetime.utcnow()
        duration_minutes = 0
        
        if interview.get("start_time"):
            duration = end_time - interview["start_time"]
            duration_minutes = int(duration.total_seconds() / 60)
        
        # Stop AI agent
        if interview.get("agent_id"):
            await self.videosdk.stop_agent(interview["agent_id"])
            
            # Get transcript from VideoSDK agent
            transcript = await self.videosdk.get_agent_transcript(interview["agent_id"])
            
            if transcript:
                # Convert VideoSDK transcript to our format
                conversation = []
                for msg in transcript:
                    conversation.append({
                        "speaker": "ai" if msg.get("role") == "assistant" else "candidate",
                        "text": msg.get("content", ""),
                        "timestamp": msg.get("timestamp", datetime.utcnow())
                    })
                
                # Update conversation in database
                await db.interviews.update_one(
                    {"_id": ObjectId(interview_id)},
                    {"$set": {"conversation": conversation}}
                )
                
                interview["conversation"] = conversation
                print(f"✅ Retrieved {len(conversation)} messages from AI agent")
        
        # End VideoSDK meeting
        if interview.get("session_id"):
            await self.videosdk.end_meeting(interview["session_id"])
        
        # Evaluate interview with Groq AI (FREE)
        evaluation = None
        if interview.get("conversation"):
            try:
                conversation = [ConversationMessage(**msg) for msg in interview["conversation"]]
                questions = [Question(**q) for q in interview.get("questions", [])]
                
                evaluation = await self.evaluation_service.evaluate_interview(
                    conversation=conversation,
                    questions=questions,
                    interview_type=interview.get("interview_type", "mixed"),
                    difficulty=interview.get("difficulty", "medium")
                )
                
                print(f"✅ Interview evaluated. Overall score: {evaluation.scores.overall_score}")
                
            except Exception as e:
                print(f"❌ Evaluation failed: {e}")
        
        # Update interview with results
        update_data = {
            "status": "completed",
            "end_time": end_time,
            "duration_minutes": duration_minutes,
            "updated_at": datetime.utcnow()
        }
        
        if evaluation:
            update_data["evaluation"] = evaluation.model_dump()
        
        result = await db.interviews.find_one_and_update(
            {"_id": ObjectId(interview_id)},
            {"$set": update_data},
            return_document=True
        )
        
        return InterviewModel(**result)
    
    async def add_message(
        self,
        interview_id: str,
        speaker: str,
        text: str,
        db
    ) -> bool:
        """
        Add message to conversation (for manual logging if needed)
        """
        message = ConversationMessage(
            speaker=speaker,
            text=text,
            timestamp=datetime.utcnow()
        )
        
        result = await db.interviews.update_one(
            {"_id": ObjectId(interview_id)},
            {
                "$push": {"conversation": message.model_dump()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0