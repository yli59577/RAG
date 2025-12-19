"""Redis 連線設定"""
from redis.asyncio import StrictRedis
from config import settings

redis_client = StrictRedis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=0,
    decode_responses=True
)
