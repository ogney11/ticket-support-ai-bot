from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base
from config import Config
from utils.logging import logger

from urllib.parse import quote_plus

DATABASE_URL = (
    f"mysql+asyncmy://{Config.MYSQL_USER}:{quote_plus(Config.MYSQL_PASSWORD)}"
    f"@{Config.MYSQL_HOST}:{Config.MYSQL_PORT}/{Config.MYSQL_DATABASE}"
    f"?charset=utf8mb4"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=False,
    pool_recycle=3600,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured (dev mode; use migrations in production).")
    except Exception as e:
        logger.error(f"init_db failed: {e}")
        raise


async def close_db():
    await engine.dispose()
