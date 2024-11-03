import redis.asyncio as redis
import mariadb
from contextlib import contextmanager, asynccontextmanager
import os
from urllib.parse import urlparse


if os.getenv('DATABASE_URL', False):
    DATABASE_URL = os.getenv('DATABASE_URL')
else:
    DATABASE_URL = 'mysql://username:password@localhost:3306/mydatabase'

if os.getenv('REDIS_URL', False):
    REDIS_URL = os.getenv('REDIS_URL')
else:
    REDIS_URL = 'redis://redis:6379'

connection = None
redis_cli = None

@contextmanager
def get_db():
    global connection
    if not connection:
        connection = mariadb.connect(
                DATABASE_URL
            )        
        # dbc = urlparse(DATABASE_URL)
        # connection = mariadb.connect(
        #         user=dbc.username,
        #         password=dbc.password,
        #         host=dbc.hostname,
        #         port=dbc.port,
        #         database=dbc.path.lstrip('/')
        #     )
    try:
        yield connection
    finally:
        pass

def close_db():
    global connection
    if connection:
        connection.close()

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