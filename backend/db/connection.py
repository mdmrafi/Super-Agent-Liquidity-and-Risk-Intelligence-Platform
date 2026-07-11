"""Async Mongo client + Beanie initialization. Call init_db() once, at
process startup (FastAPI's startup event, or top of a standalone script's
main()). Beanie 2.x runs on pymongo's own async client (pymongo >=4.9) --
no separate motor dependency needed."""
import os

from beanie import init_beanie
from dotenv import load_dotenv
from pymongo import AsyncMongoClient

from .models import Transaction, User

load_dotenv()

_client: AsyncMongoClient | None = None


def get_client() -> AsyncMongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI is not set (check .env)")
        _client = AsyncMongoClient(uri)
    return _client


async def init_db():
    db_name = os.getenv("MONGODB_DB_NAME", "Super_agent")
    await init_beanie(database=get_client()[db_name], document_models=[User, Transaction])
