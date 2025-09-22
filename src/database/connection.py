from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.core import config
from .schema import Base

# Create an asynchronous engine for the database connection.
# The URL is pulled from our central configuration.
engine = create_async_engine(config.DATABASE_URL, echo=False)

# Create a configured "Session" class.
# This will be used to create individual database sessions.
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


async def create_db_and_tables():
    """
    Asynchronously creates all database tables defined in the Base metadata.
    This is typically called on application startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
