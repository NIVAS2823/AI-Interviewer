from motor.motor_asyncio import AsyncIOMotorClient
from redis import asyncio as aioredis
from app.core.config import settings
import logging

logger = logging.getLogger("uvicorn")


# MongoDB and Redis clients
mongodb_client: AsyncIOMotorClient = None
database = None
redis_client = None


# =============================
# 🧠 MongoDB Connection
# =============================
async def connect_to_mongo():
    """Connect to MongoDB asynchronously"""
    global mongodb_client, database
    mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
    database = mongodb_client.get_default_database()
    logger.info("✅ Connected to MongoDB")


async def close_mongo_connection():
    """Close MongoDB connection"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        logger.info("❌ Closed MongoDB connection")


# =============================
# ⚙️ Redis Connection (async)
# =============================
async def connect_to_redis():
    """Connect to Redis asynchronously"""
    global redis_client
    redis_client = await aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True
    )
    logger.info("✅ Connected to Redis")


async def close_redis_connection():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("❌ Closed Redis connection")


# =============================
# 🔁 Utility Getters
# =============================
def get_database():
    """Get MongoDB database instance"""
    return database


def get_redis():
    """Get Redis client instance"""
    return redis_client
