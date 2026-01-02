from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import (
    connect_to_mongo,
    close_mongo_connection,
    connect_to_redis,
    close_redis_connection,
)
from app.api.v1 import health, auth,resume,interview,evaluation,websocket,agent_memory

from dotenv import load_dotenv


load_dotenv()


# =========================
# 🧠 LOGGING CONFIGURATION
# =========================
logging.basicConfig(
    level=logging.INFO,  # or DEBUG for more detail
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Use Uvicorn's logger so it shows in Docker & terminal logs
logger = logging.getLogger("uvicorn")


# =========================
# 🚀 APP LIFESPAN HANDLER
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events"""
    logger.info("🚀 AI Interviewer Platform API starting...")
    logger.info(f"📝 Environment: {settings.ENVIRONMENT}")

    # Connect to databases
    try:
        await connect_to_mongo()
        await connect_to_redis()
        logger.info("✅ Connected to MongoDB and Redis successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to connect to databases: {e}")

    logger.info(f"📚 API Docs available at: http://localhost:8000/docs")
    logger.info("✅ Application startup complete.")

    # Yield control to the app runtime
    yield

    # Shutdown phase
    logger.info("👋 AI Interviewer Platform API shutting down...")
    try:
        await close_mongo_connection()
        await close_redis_connection()
        logger.info("✅ Shutdown complete. All resources closed gracefully.")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


# =========================
# ⚙️ FASTAPI INITIALIZATION
# =========================
app = FastAPI(
    title="AI Interviewer Platform API",
    description="Intelligent automated interview system with VideoSDK agents.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# =========================
# 🌐 CORS CONFIGURATION
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 📦 ROUTERS
# =========================
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(resume.router,prefix="/api/v1/resume",tags=["Resume"])
app.include_router(interview.router, prefix="/api/v1/interview", tags=["Interview"])
app.include_router(evaluation.router, prefix="/api/v1/evaluation", tags=["Evaluation"])
app.include_router(websocket.router, prefix="/api/v1", tags=["WebSocket"])
app.include_router(agent_memory.router, prefix="/api/v1",tags=["Agent-Memory"]) 


# =========================
# 🏠 ROOT ENDPOINT
# =========================
@app.get("/")
async def root():
    """Root endpoint for health and metadata"""
    return {
        "message": "AI Interviewer Platform API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }
