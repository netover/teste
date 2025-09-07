from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

from src.core import config

# Create an async engine instance.
# The `echo=True` flag is useful for debugging SQL statements.
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False, # Set to True to see generated SQL in logs
    future=True
)

# Create a configured "Session" class.
# This is the factory for new async session objects.
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for our models.
# The actual models are in src/models/database.py and will inherit from this.
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    It ensures the session is always closed after the request is finished.
    """
    async with AsyncSessionLocal() as session:
        yield session
