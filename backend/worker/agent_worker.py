import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import jwt

# ---------------------------------------------------
# Logging
# ---------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("agent-worker")

# ---------------------------------------------------
# ENV VARS
# ---------------------------------------------------
VIDEOSDK_API_KEY = os.getenv("VIDEOSDK_API_KEY")
VIDEOSDK_SECRET_KEY = os.getenv("VIDEOSDK_SECRET_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# ---------------------------------------------------
# In-Memory Storage
# ---------------------------------------------------
AGENTS: Dict[str, Dict] = {}  # agent_id -> agent_data
TRANSCRIPTS: Dict[str, List[Dict]] = {}  # agent_id -> messages

# ---------------------------------------------------
# FastAPI App
# ---------------------------------------------------
app = FastAPI(title="Self-Hosted AI Agent Worker", version="1.0.0")


# ---------------------------------------------------
# Request Schemas
# ---------------------------------------------------
class AgentCreateRequest(BaseModel):
    roomId: str
    name: str
    instructions: str
    questions: List[Dict]
    avatar: Dict
    voice: Dict
    stt: Dict
    llm: Dict
    settings: Dict


class AgentStartRequest(BaseModel):
    agentId: str
    roomId: str


class AgentStopRequest(BaseModel):
    agentId: str


# ---------------------------------------------------
# Health Check
# ---------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "worker": "running",
        "agents_active": len(AGENTS),
        "groq_configured": bool(GROQ_API_KEY),
        "deepgram_configured": bool(DEEPGRAM_API_KEY)
    }


# ---------------------------------------------------
# Create Agent
# ---------------------------------------------------
@app.post("/create")
async def create_agent(req: AgentCreateRequest):
    """Create a new AI agent instance"""
    
    agent_id = f"agent_{int(time.time() * 1000)}"
    
    # Store agent configuration
    AGENTS[agent_id] = {
        "id": agent_id,
        "room_id": req.roomId,
        "name": req.name,
        "instructions": req.instructions,
        "questions": req.questions,
        "voice": req.voice,
        "stt": req.stt,
        "llm": req.llm,
        "settings": req.settings,
        "status": "created",
        "current_question_index": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Initialize transcript
    TRANSCRIPTS[agent_id] = []
    
    logger.info(f"✅ Agent created: {agent_id} for room {req.roomId}")
    
    return {
        "agentId": agent_id,
        "status": "created",
        "message": f"Agent {req.name} created successfully"
    }


# ---------------------------------------------------
# Start Agent
# ---------------------------------------------------
@app.post("/start")
async def start_agent(req: AgentStartRequest):
    """Start the AI agent in the VideoSDK room"""
    
    agent_id = req.agentId
    
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = AGENTS[agent_id]
    agent["status"] = "active"
    
    # Add greeting to transcript
    greeting = f"Hello! I'm {agent['name']}, and I'll be conducting your interview today. Let's begin with the first question."
    
    TRANSCRIPTS[agent_id].append({
        "role": "assistant",
        "content": greeting,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Add first question
    if agent["questions"]:
        first_question = agent["questions"][0].get("text", "Tell me about yourself.")
        TRANSCRIPTS[agent_id].append({
            "role": "assistant",
            "content": first_question,
            "timestamp": datetime.utcnow().isoformat()
        })
        agent["current_question_index"] = 0
    
    logger.info(f"✅ Agent started: {agent_id}")
    
    return {
        "status": True,
        "message": "Agent started successfully",
        "agentId": agent_id
    }


# ---------------------------------------------------
# Stop Agent
# ---------------------------------------------------
@app.post("/stop")
async def stop_agent(req: AgentStopRequest):
    """Stop the AI agent"""
    
    agent_id = req.agentId
    
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = AGENTS[agent_id]
    agent["status"] = "stopped"
    
    # Add closing message to transcript
    TRANSCRIPTS[agent_id].append({
        "role": "assistant",
        "content": "Thank you for your time today. The interview is now complete. Good luck!",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    logger.info(f"✅ Agent stopped: {agent_id}")
    
    return {
        "status": True,
        "message": "Agent stopped successfully",
        "agentId": agent_id
    }


# ---------------------------------------------------
# Get Transcript
# ---------------------------------------------------
@app.get("/transcript/{agent_id}")
async def get_transcript(agent_id: str):
    """Get conversation transcript for an agent"""
    
    if agent_id not in TRANSCRIPTS:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    return {
        "agentId": agent_id,
        "transcript": TRANSCRIPTS[agent_id],
        "message_count": len(TRANSCRIPTS[agent_id])
    }


# ---------------------------------------------------
# Simulate Conversation (for testing)
# ---------------------------------------------------
@app.post("/simulate/{agent_id}")
async def simulate_conversation(agent_id: str):
    """Simulate a conversation for testing purposes"""
    
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = AGENTS[agent_id]
    
    if agent["status"] != "active":
        raise HTTPException(status_code=400, detail="Agent must be active")
    
    # Simulate candidate responses for all questions
    questions = agent["questions"]
    
    for i, question in enumerate(questions):
        question_text = question.get("text", "")
        
        # Simulate candidate answer
        candidate_answer = await _generate_simulated_answer(question_text, agent["instructions"])
        
        TRANSCRIPTS[agent_id].append({
            "role": "user",
            "content": candidate_answer,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Generate AI follow-up or move to next question
        if i < len(questions) - 1:
            # Move to next question
            next_question = questions[i + 1].get("text", "")
            TRANSCRIPTS[agent_id].append({
                "role": "assistant",
                "content": f"Thank you for that answer. {next_question}",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            # Last question - thank the candidate
            TRANSCRIPTS[agent_id].append({
                "role": "assistant",
                "content": "Thank you for your detailed answers. That concludes our interview today.",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    agent["current_question_index"] = len(questions)
    
    logger.info(f"✅ Simulated conversation for agent {agent_id}")
    
    return {
        "status": True,
        "message": "Conversation simulated successfully",
        "message_count": len(TRANSCRIPTS[agent_id])
    }


# ---------------------------------------------------
# Helper: Generate Simulated Answer using Groq
# ---------------------------------------------------
async def _generate_simulated_answer(question: str, context: str) -> str:
    """Generate a simulated candidate answer using Groq AI"""
    
    if not GROQ_API_KEY:
        # Fallback generic answer
        return "That's an interesting question. Based on my experience, I would approach this by first analyzing the requirements, then designing a solution that addresses the key challenges while maintaining scalability and performance."
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a skilled software engineer being interviewed. Provide realistic, detailed answers that demonstrate your experience and knowledge. Keep answers 2-3 sentences long."
                        },
                        {
                            "role": "user",
                            "content": f"Interview question: {question}\n\nProvide a realistic candidate answer."
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 200
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Groq API error: {response.status_code}")
                return "Based on my experience, I believe the best approach would be to analyze the problem systematically and implement a solution that balances efficiency with maintainability."
    
    except Exception as e:
        logger.exception(f"Error generating simulated answer: {e}")
        return "I would approach this challenge by leveraging my technical skills and experience to develop an effective solution."


# ---------------------------------------------------
# Process Candidate Message (for real-time)
# ---------------------------------------------------
@app.post("/process_message/{agent_id}")
async def process_message(agent_id: str, message: Dict):
    """Process a candidate's message and generate AI response"""
    
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = AGENTS[agent_id]
    
    if agent["status"] != "active":
        raise HTTPException(status_code=400, detail="Agent is not active")
    
    candidate_text = message.get("text", "")
    
    # Add candidate message to transcript
    TRANSCRIPTS[agent_id].append({
        "role": "user",
        "content": candidate_text,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Generate AI response
    ai_response = await _generate_ai_response(agent, candidate_text)
    
    # Add AI response to transcript
    TRANSCRIPTS[agent_id].append({
        "role": "assistant",
        "content": ai_response,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "status": True,
        "response": ai_response,
        "agentId": agent_id
    }


async def _generate_ai_response(agent: Dict, candidate_text: str) -> str:
    """Generate AI interviewer response using Groq"""
    
    if not GROQ_API_KEY:
        # Fallback: move to next question or acknowledge
        current_idx = agent["current_question_index"]
        questions = agent["questions"]
        
        if current_idx < len(questions) - 1:
            agent["current_question_index"] += 1
            next_q = questions[agent["current_question_index"]].get("text", "")
            return f"I see. Let's move on. {next_q}"
        else:
            return "Thank you for your answer. That concludes our interview."
    
    try:
        # Build conversation context
        conversation_history = TRANSCRIPTS[agent["id"]][-6:]  # Last 3 exchanges
        
        messages = [
            {
                "role": "system",
                "content": agent["instructions"]
            }
        ]
        
        # Add recent history
        for msg in conversation_history[:-1]:  # Exclude the last one (just added)
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current candidate response
        messages.append({
            "role": "user",
            "content": candidate_text
        })
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 150
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                ai_text = data["choices"][0]["message"]["content"]
                
                # Update question index if we detect we're moving forward
                if "next question" in ai_text.lower() or "let's move" in ai_text.lower():
                    if agent["current_question_index"] < len(agent["questions"]) - 1:
                        agent["current_question_index"] += 1
                
                return ai_text
            else:
                logger.error(f"Groq API error: {response.status_code}")
                return "I see. Could you elaborate on that?"
    
    except Exception as e:
        logger.exception(f"Error generating AI response: {e}")
        return "Thank you for sharing that. Let's continue."


# ---------------------------------------------------
# Startup Event
# ---------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("🤖 AI Agent Worker Starting...")
    logger.info(f"📡 Groq API: {'✅ Configured' if GROQ_API_KEY else '❌ Missing'}")
    logger.info(f"🎙️  Deepgram API: {'✅ Configured' if DEEPGRAM_API_KEY else '❌ Missing'}")
    logger.info(f"📹 VideoSDK API: {'✅ Configured' if VIDEOSDK_API_KEY else '❌ Missing'}")
    logger.info("=" * 50)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)