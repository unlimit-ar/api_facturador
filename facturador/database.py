import redis.asyncio as redis
from contextlib import contextmanager, asynccontextmanager

REDIS_URL = 'redis://facturador_redis:6379'

redis_cli = None

async def close_redis():
    global redis_cli
    if redis_cli:
        redis_cli.close()
        await redis_cli.wait_closed()

@asynccontextmanager
async def get_redis():
    global redis_cli
    if not redis_cli:
        redis_cli = await redis.from_url(REDIS_URL)
    try:
        yield redis_cli
    finally:
        pass