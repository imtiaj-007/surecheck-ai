import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter

from src.core.config import settings
from src.utils.limiter import get_real_ip
from src.utils.logger import log

# Global variable to hold the Redis connection
redis_client: redis.Redis | None = None


async def create_redis_client() -> redis.Redis:
    """
    Create and return an asynchronous Redis client using the settings.REDIS_URL.

    Returns:
        redis.Redis: An instance of the asynchronous Redis client.

    Raises:
        Exception: If the connection to Redis fails.
    """
    try:
        log.info(f"🔌 Connecting to Redis at {settings.REDIS_URL}...")
        client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5.0,
        )
        await client.ping()
        log.info("✅ Connected to Redis successfully")
        return client
    except Exception as e:
        log.error(f"❌ Failed to connect to Redis: {e}")
        raise e


async def setup_fastapi_limiter(redis_instance: redis.Redis) -> None:
    """
    Initialize the FastAPI Rate Limiter with the given Redis instance.

    Args:
        redis_instance (redis.Redis): The Redis client to use for rate limiting.

    Raises:
        Exception: If initialization of FastAPI Limiter fails.
    """
    try:
        await FastAPILimiter.init(redis_instance, identifier=get_real_ip)
        log.info("🛡️ FastAPI Rate Limiter initialized successfully")
    except Exception as e:
        log.error(f"❌ Failed to initialize FastAPI Limiter: {e}")
        raise e


async def init_redis() -> None:
    """
    Initialize Redis connection and FastAPI Limiter.
    This should be called during application startup.

    Raises:
        Exception: If Redis or FastAPI Limiter initialization fails.
    """
    global redis_client
    try:
        redis_client = await create_redis_client()
        await setup_fastapi_limiter(redis_client)
    except Exception as e:
        log.error(f"❌ Redis/Rate Limiter initialization failed: {e}")
        raise e


async def close_redis() -> None:
    """
    Close Redis connection.
    This should be called during application shutdown.
    If no Redis connection exists, this function does nothing.

    Returns:
        None
    """
    global redis_client
    if redis_client:
        try:
            log.info("🛑 Closing Redis connection...")
            await redis_client.close()
            log.info("✅ Redis connection closed")
        except Exception as e:
            log.error(f"❌ Error closing Redis connection: {e}")
