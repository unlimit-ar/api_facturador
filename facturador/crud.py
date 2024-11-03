import asyncio
import json

from typing import List
from datetime import datetime
from database import get_db, get_redis
from schemas.schemas import UserCreate, LoginCreate
from tools.session import UserSession

EXPIRE = 600

def run_query(query, *args):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, args)
        result = cursor.fetchall()
        cursor.close()
        return result

def run_command(command, *args):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(command, *args)
        conn.commit()
        cursor.close()

async def get_user_by_email(email: str):
    result = await asyncio.to_thread(run_query, "SELECT * FROM users WHERE email = ?", email)
    return result[0] if result else None

async def create_user(user: UserCreate):
    await asyncio.to_thread(run_command, "INSERT INTO users (name, email) VALUES (?, ?)", user.name, user.email)
    result = await asyncio.to_thread(run_query, "SELECT * FROM users WHERE email = ?", user.email)
    return result[0] if result else None

async def get_users(skip: int = 0, limit: int = 10) -> List[dict]:
    result = await asyncio.to_thread(run_query, "SELECT * FROM users LIMIT ? OFFSET ?", limit, skip)
    return [dict(id=row[0], name=row[1], email=row[2]) for row in result]

async def create_token(samaccountname: str = '', token: str = ''):
    async with get_redis() as redis:
        res = await redis.set(f"token:{samaccountname}", token)
    return res

async def get_token(samaccountname: str):
    async with get_redis() as redis:
        token = await redis.get(f"token:{samaccountname}")  # Usa await aquí
        if token:
            return token
    return None

async def create_login(user: UserSession, hash_password: str):
    values = (user.samaccountname, user.app_name, user.ou)
    command = "INSERT INTO login (samaccountname, app_name, ou) VALUES (?, ?, ?)"
    await asyncio.to_thread(run_command, command, values)
    async with get_redis() as redis:
        await redis.set(f"token:{user.samaccountname}", user.token, ex=EXPIRE)
        await redis.set(f"password:{user.samaccountname}", hash_password, ex=EXPIRE)
    return None

async def check_token(samaccountname: str, token: str):
    async with get_redis() as redis:
        _token = await redis.get(f"token:{samaccountname}")
        if _token.decode('utf8') == str(token): 
            await redis.expire(f"token:{samaccountname}", xx=True, time=EXPIRE )
            res = await redis.expire(f"password:{samaccountname}", xx=True, time=EXPIRE)
            if res:
                return res
    return False