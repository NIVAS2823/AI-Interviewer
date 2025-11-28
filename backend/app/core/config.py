from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = "development"

    # Database
    MONGODB_URL: str = "mongodb://mongodb:27017/ai_interviewer"
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200

    # Groq AI
    GROQ_API_KEY: str = ""

    # Deepgram STT (NEW)
    DEEPGRAM_API_KEY: str = ""

    # Azure TTS (NEW)
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = ""

    #Google TTS
    GOOGLE_TTS_API_KEY:str=""

    # Cloudflare R2 (NEW)
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_ENDPOINT: str = ""
    R2_BUCKET_NAME: str = ""
    R2_PUBLIC_URL: str = ""

     # VideoSDK
    VIDEOSDK_API_KEY: str = ""
    VIDEOSDK_SECRET_KEY: str = ""
    VIDEOSDK_WEBHOOK_SECRET: str = ""
    VIDEOSDK_API_URL: str = "https://api.videosdk.live/v2"


     # Agent Worker
    AGENT_WORKER_URL: str = "http://agent_worker:9000"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    def split_cors(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [s.strip() for s in v.split(",")]
        return v

    # File Upload
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE: int = 10485760
    ALLOWED_EXTENSIONS: str = ".pdf"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
