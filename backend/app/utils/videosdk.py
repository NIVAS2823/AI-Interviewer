import httpx
from typing import Dict, Optional, List
from app.core.config import settings
import json


class VideoSDKAgentService:
    """
    Enhanced VideoSDK integration for AI-powered video interviews
    Supports AI agents with STT, TTS, and LLM integration
    """
    
    BASE_URL = "https://api.videosdk.live/v2"
    
    def __init__(self):
        """Initialize VideoSDK service"""
        self.api_key = settings.VIDEOSDK_API_KEY
        
        if not self.api_key:
            print("⚠️ VIDEOSDK_API_KEY not set - video features disabled")
            print("Get free API key at: https://app.videosdk.live/signup")
        else:
            print("✅ VideoSDK Agent service initialized (FREE tier)")
    
    async def create_meeting(self) -> Optional[str]:
        """
        Create a VideoSDK meeting room
        
        Returns:
            Meeting ID (roomId)
        """
        if not self.api_key:
            print("⚠️ VideoSDK disabled - no API key")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/rooms",
                    headers={
                        "Authorization": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    meeting_id = data.get("roomId")
                    print(f"✅ VideoSDK meeting created: {meeting_id}")
                    return meeting_id
                else:
                    print(f"❌ VideoSDK meeting creation failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ VideoSDK error: {e}")
            return None
    
    async def get_meeting_token(self, meeting_id: str, permissions: List[str] = None) -> Optional[str]:
        """
        Generate auth token for meeting
        
        Args:
            meeting_id: VideoSDK meeting ID
            permissions: List of permissions
            
        Returns:
            JWT token for meeting access
        """
        if not self.api_key:
            return None
        
        if permissions is None:
            permissions = [
                "allow_join",
                "allow_mod",
                "ask_join"
            ]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/get-token",
                    headers={
                        "Authorization": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "roomId": meeting_id,
                        "permissions": permissions
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    token = data.get("token")
                    print(f"✅ Meeting token generated for: {meeting_id}")
                    return token
                else:
                    print(f"❌ Token generation failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Token generation error: {e}")
            return None
    
    async def create_ai_agent(
        self,
        meeting_id: str,
        interviewer_name: str,
        questions: List[str],
        system_prompt: str,
        voice_id: str = "en-US-Neural2-F"
    ) -> Optional[str]:
        """
        Create AI agent for the interview with real-time capabilities
        
        Args:
            meeting_id: VideoSDK meeting ID
            interviewer_name: Name of AI interviewer
            questions: List of interview questions
            system_prompt: System prompt for AI behavior
            voice_id: Voice ID for TTS
            
        Returns:
            Agent ID
        """
        if not self.api_key:
            return None
        
        # Agent configuration
        agent_config = {
            "roomId": meeting_id,
            "name": interviewer_name,
            "characteristics": {
                "voice": voice_id,
                "personality": "professional",
                "style": "conversational"
            },
            "llm": {
                "provider": "custom",  # We'll use Groq
                "model": "llama-3.1-70b-versatile",
                "systemPrompt": system_prompt,
                "temperature": 0.7
            },
            "stt": {
                "provider": "deepgram",  # VideoSDK supports Deepgram
                "language": "en-US"
            },
            "tts": {
                "provider": "google",
                "voice": voice_id,
                "speed": 1.0
            },
            "avatar": {
                "type": "default",
                "style": "professional"
            },
            "initialMessages": [
                f"Hello! I'm {interviewer_name}, your AI interviewer today. I'll be asking you {len(questions)} questions. Let's begin when you're ready."
            ],
            "questions": questions
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/agents",
                    headers={
                        "Authorization": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=agent_config,
                    timeout=30.0
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    agent_id = data.get("agentId") or data.get("id")
                    print(f"✅ AI Agent created: {agent_id}")
                    return agent_id
                else:
                    print(f"❌ Agent creation failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Agent creation error: {e}")
            return None
    
    async def start_agent(self, meeting_id: str, agent_id: str) -> bool:
        """
        Start the AI agent in the meeting
        
        Args:
            meeting_id: Meeting ID
            agent_id: Agent ID
            
        Returns:
            True if successful
        """
        if not self.api_key:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/agents/{agent_id}/start",
                    headers={
                        "Authorization": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "roomId": meeting_id
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    print(f"✅ Agent started: {agent_id}")
                    return True
                else:
                    print(f"❌ Agent start failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Agent start error: {e}")
            return False
    
    async def stop_agent(self, agent_id: str) -> bool:
        """
        Stop the AI agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            True if successful
        """
        if not self.api_key:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/agents/{agent_id}/stop",
                    headers={
                        "Authorization": self.api_key,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    print(f"✅ Agent stopped: {agent_id}")
                    return True
                else:
                    print(f"❌ Agent stop failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Agent stop error: {e}")
            return False
    
    async def get_agent_transcript(self, agent_id: str) -> Optional[List[Dict]]:
        """
        Get conversation transcript from agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of conversation messages
        """
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/agents/{agent_id}/transcript",
                    headers={
                        "Authorization": self.api_key
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("transcript", [])
                else:
                    print(f"❌ Transcript retrieval failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Transcript error: {e}")
            return None
    
    async def end_meeting(self, meeting_id: str) -> bool:
        """
        End a meeting
        
        Args:
            meeting_id: VideoSDK meeting ID
            
        Returns:
            True if successful
        """
        if not self.api_key:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/rooms/{meeting_id}/end",
                    headers={
                        "Authorization": self.api_key,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    print(f"✅ Meeting ended: {meeting_id}")
                    return True
                else:
                    print(f"❌ End meeting failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ End meeting error: {e}")
            return False
    
    def build_system_prompt(
        self,
        interviewer_name: str,
        interview_type: str,
        questions: List[str],
        candidate_info: Dict
    ) -> str:
        """
        Build comprehensive system prompt for AI agent
        
        Args:
            interviewer_name: Name of interviewer
            interview_type: Type of interview
            questions: List of questions
            candidate_info: Candidate resume data
            
        Returns:
            System prompt string
        """
        
        prompt = f"""You are {interviewer_name}, a professional and friendly AI interviewer conducting a {interview_type} interview.

INTERVIEW STRUCTURE:
- You will ask exactly {len(questions)} questions in order
- Wait for the candidate to fully answer before moving to the next question
- Be encouraging and professional
- If the answer is unclear, ask ONE follow-up question for clarification
- Keep the conversation flowing naturally

CANDIDATE BACKGROUND:
{json.dumps(candidate_info, indent=2)}

QUESTIONS TO ASK (IN ORDER):
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(questions)])}

BEHAVIOR GUIDELINES:
1. Start with a warm greeting and explain the format
2. Ask questions ONE AT A TIME
3. Listen actively - acknowledge good points
4. If candidate struggles, provide gentle encouragement
5. After each answer, briefly acknowledge before moving on
6. After the last question, thank them and explain next steps
7. Keep responses concise - you're the interviewer, not the interviewee
8. Be professional but conversational
9. Avoid technical jargon unless discussing technical topics
10. End the interview gracefully after all questions

RESPONSE FORMAT:
- Keep your questions and comments brief (1-3 sentences)
- Don't repeat or rephrase the candidate's answer
- Use natural conversational language
- Show empathy and understanding

Remember: Your goal is to conduct a professional interview that makes the candidate feel comfortable while gathering comprehensive information about their qualifications.
"""
        
        return prompt