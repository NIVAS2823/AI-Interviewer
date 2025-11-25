import os
import time
import hmac
import jwt
import httpx
import hashlib
import asyncio
import logging

from typing import Dict, Optional, List, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# -------------------------------------------------
# Global Config
# -------------------------------------------------
API_URL = settings.VIDEOSDK_API_URL.rstrip("/")
API_KEY = settings.VIDEOSDK_API_KEY
SECRET_KEY = settings.VIDEOSDK_SECRET_KEY
WEBHOOK_SECRET = settings.VIDEOSDK_WEBHOOK_SECRET


def auth_header() -> Dict[str, str]:
    """Bearer <API_KEY> for VideoSDK APIs"""
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }


class VideoSDKAgentService:
    """
    Safe, clean helper for:
    - Creating rooms
    - Generating join tokens
    - Creating/stopping AI Agents
    """

    def __init__(self):
        self.api_url = API_URL
        self.api_key = API_KEY
        self.secret_key = SECRET_KEY
        self.webhook_secret = WEBHOOK_SECRET

        if not self.api_key:
            logger.warning("⚠️ VIDEOSDK_API_KEY missing, video features disabled")

        logger.info(f"VideoSDKAgentService initialized (url={self.api_url})")

    # -------------------------------------------------
    # Build System Prompt
    # -------------------------------------------------
    def build_system_prompt(
        self,
        interviewer_name: str,
        interview_type: str,
        questions: List[str],
        candidate_info: Dict[str, Any]
    ) -> str:
        candidate_name = candidate_info.get("name", "Candidate")
        skills = ", ".join(candidate_info.get("skills", [])[:5])
        experience_years = candidate_info.get("experience_years", 0)
        education = "; ".join(candidate_info.get("education", []))

        prompt = f"""
You are {interviewer_name}, a professional and friendly technical interviewer conducting a {interview_type} interview.

CANDIDATE INFORMATION:
- Name: {candidate_name}
- Skills: {skills}
- Experience: {experience_years} years
- Education: {education}

YOUR ROLE:
1. You are conducting a structured interview with pre-defined questions
2. Ask questions one at a time from the question list below
3. Listen carefully to the candidate's answers
4. Provide brief acknowledgments ("I see", "That's interesting", "Thank you")
5. Ask ONE follow-up question if the answer needs clarification (keep it short)
6. Move to the next question after getting a satisfactory answer
7. Be professional, encouraging, and respectful throughout

INTERVIEW QUESTIONS (ask in order):
{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}

CONVERSATION STYLE:
- Keep your responses concise (1-2 sentences)
- Don't repeat the candidate's answer back to them
- Don't give lengthy explanations
- Focus on listening and moving the interview forward
- End the interview naturally after all questions are covered

START: Begin by greeting the candidate and asking the first question.
"""
        return prompt.strip()

    # -------------------------------------------------
    # JWT Token Generator
    # -------------------------------------------------
    def generate_jwt(self, roles: List[str], permissions: List[str]) -> Optional[str]:
        if not self.api_key or not self.secret_key:
            logger.error("❌ Missing API_KEY or SECRET_KEY")
            return None

        now = int(time.time())
        payload = {
            "apikey": self.api_key,
            "iat": now,
            "exp": now + 60 * 60 * 24,
            "version": 2,
            "roles": roles,
            "permissions": permissions,
        }

        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    # -------------------------------------------------
    # HTTP Helpers
    # -------------------------------------------------
    async def _post(self, url: str, payload: Dict[str, Any]):
        try:
            async with httpx.AsyncClient() as client:
                return await client.post(url, json=payload, headers=auth_header(), timeout=30)
        except Exception as e:
            logger.exception(f"POST {url} failed: {e}")
            return None

    async def _get(self, url: str):
        try:
            async with httpx.AsyncClient() as client:
                return await client.get(url, headers=auth_header(), timeout=30)
        except Exception as e:
            logger.exception(f"GET {url} failed: {e}")
            return None

    # -------------------------------------------------
    # Webhook Signature
    # -------------------------------------------------
    def verify_webhook_signature(self, raw_body: bytes, signature: Optional[str]) -> bool:
        if not self.webhook_secret:
            return True

        if not signature:
            return False

        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    # -------------------------------------------------
    # Create Meeting
    # -------------------------------------------------
    async def create_meeting(self) -> Optional[str]:
        jwt_token = self.generate_jwt(
            roles=["crawler"],
            permissions=["allow_join", "allow_mod", "ask_join"]
        )

        if not jwt_token:
            logger.error("Cannot create meeting — JWT missing")
            return None

        url = f"{self.api_url}/rooms"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={},
                    headers={"Authorization": jwt_token, "Content-Type": "application/json"},
                    timeout=25,
                )

                if resp.status_code in (200, 201):
                    room_id = resp.json().get("roomId")
                    logger.info(f"Room Created: {room_id}")
                    return room_id

                logger.error(f"create_meeting error {resp.status_code}: {resp.text}")
                return None

        except Exception as e:
            logger.exception(f"create_meeting failed: {e}")
            return None

    # -------------------------------------------------
    # Generate RTC Join Token
    # -------------------------------------------------
    async def get_meeting_token(self, meeting_id: str) -> Optional[str]:
        jwt_token = self.generate_jwt(
            roles=["rtc"],
            permissions=["allow_join", "allow_mod"]
        )

        if not jwt_token:
            logger.error("get_meeting_token failed — missing keys")
            return None

        logger.info(f"RTC token generated for room {meeting_id}")
        return jwt_token

    # -------------------------------------------------
    # Create AI Agent (Worker)
    # -------------------------------------------------
    async def create_ai_agent(
        self,
        meeting_id: str,
        interviewer_name: str,
        questions: List[str],
        system_prompt: str,
        voice: str = "alloy",
        avatar: str = "professional",
        model: str = "llama-3.3-70b-versatile",
        stt_provider: str = "whisper",
        tts_provider: str = "coqui",
        temperature: float = 0.5,
    ) -> Optional[str]:

        worker_url = os.getenv("AGENT_WORKER_URL", "http://agent_worker:9000")

        agent_payload = {
            "roomId": meeting_id,
            "name": interviewer_name,
            "instructions": system_prompt,
            "questions": [{"text": q} for q in questions],
            "avatar": {"style": avatar},
            "voice": {"provider": tts_provider, "voiceId": voice},
            "stt": {"provider": stt_provider, "language": "en-US"},
            "llm": {"provider": "groq", "model": model, "temperature": temperature},
            "settings": {"followUp": True, "listenWhileSpeaking": False},
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{worker_url}/create", json=agent_payload, timeout=30)

                if resp.status_code in (200, 201):
                    agent_id = resp.json().get("agentId")
                    logger.info(f"Self-hosted Agent created: {agent_id}")
                    return agent_id

                logger.error(f"create_ai_agent worker error {resp.status_code}: {resp.text}")
                return None

        except Exception as e:
            logger.exception(f"create_ai_agent worker failed: {e}")
            return None

    # -------------------------------------------------
    # Start Agent
    # -------------------------------------------------
    async def start_agent(self, meeting_id: str, agent_id: str) -> bool:
        worker_url = os.getenv("AGENT_WORKER_URL", "http://agent_worker:9000")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{worker_url}/start",
                    json={"agentId": agent_id, "roomId": meeting_id},
                    timeout=20
                )

                if resp.status_code in (200, 201):
                    logger.info(f"Agent started: {agent_id}")
                    return True

                logger.error(f"start_agent worker error {resp.status_code}")
                return False

        except Exception as e:
            logger.exception(f"start_agent error: {e}")
            return False

    # -------------------------------------------------
    # Stop Agent
    # -------------------------------------------------
    async def stop_agent(self, agent_id: str) -> bool:
        worker_url = os.getenv("AGENT_WORKER_URL", "http://agent_worker:9000")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{worker_url}/stop",
                    json={"agentId": agent_id},
                    timeout=20
                )

                if resp.status_code in (200, 201):
                    logger.info(f"Agent stopped: {agent_id}")
                    return True

                logger.error(f"stop_agent error {resp.status_code}")
                return False

        except Exception as e:
            logger.exception(f"stop_agent failed: {e}")
            return False

    # -------------------------------------------------
    # End Meeting
    # -------------------------------------------------
    async def end_meeting(self, meeting_id: str) -> bool:
        jwt_token = self.generate_jwt(
            roles=["crawler"], permissions=["allow_mod", "allow_join"]
        )

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.api_url}/rooms/{meeting_id}/end",
                    json={},
                    headers={"Authorization": jwt_token, "Content-Type": "application/json"},
                )

                if resp.status_code in (200, 201):
                    logger.info(f"Meeting ended: {meeting_id}")
                    return True

                logger.error(f"end_meeting API error: {resp.text}")
                return False

        except Exception as e:
            logger.exception(f"end_meeting failed: {e}")
            return False

    # -------------------------------------------------
    # Transcript
    # -------------------------------------------------
    async def get_agent_transcript(self, agent_id: str) -> Optional[List[Dict]]:
        worker_url = os.getenv("AGENT_WORKER_URL", "http://agent_worker:9000")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{worker_url}/transcript/{agent_id}", timeout=20)

                if resp.status_code == 200:
                    return resp.json().get("transcript", [])

                logger.warning(f"Transcript not available: {resp.text}")
                return None

        except Exception as e:
            logger.exception(f"get_agent_transcript failed: {e}")
            return None
