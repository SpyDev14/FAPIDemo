from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm         import declarative_base

from app.core.config import settings


Base: type[type] = declarative_base()

_engine = create_async_engine(
    url=settings.asyncpg_db_url,
    echo=settings.DEBUG,
)

_async_session_maker = async_sessionmaker(
    _engine, expire_on_commit=False
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session_maker() as session:
        yield session
