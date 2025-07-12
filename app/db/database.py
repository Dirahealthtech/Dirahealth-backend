from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .base import Base
from ..core.config import Config


DATABASE_URL = Config.DATABASE_URL

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

