import asyncio
import json

from typing import List
from datetime import datetime
from database import get_db, get_redis
from schemas.schemas import UserCreate, LoginCreate
from tools.session import UserSession

EXPIRE = 180000

async def add_token(cuit: str, token: str):
    async with get_redis() as redis:
        await redis.set(f"cuit:{cuit}", token, ex=EXPIRE)
    return None

async def get_token(cuit: str):
    async with get_redis() as redis:
        res = await redis.get(f"cuit:{cuit}")
        if res:
            return res.decode('utf-8')
        return None
    return False