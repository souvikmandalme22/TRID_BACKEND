from app.models import *
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from app.core.config import settings
import logging

logger = logging.getLogger("trid")


class Base(DeclarativeBase):
    pass


def _build_engine():
    pool_class = NullPool if settings.APP_ENV == "testing" else AsyncAdaptedQueuePool

    kwargs = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,
    }

    if pool_class is not NullPool:
        kwargs.update({
            "poolclass": pool_class,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        })
    else:
        kwargs["poolclass"] = NullPool

    return create_async_engine(settings.DATABASE_URL, **kwargs)


engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        logger.info("Database connection established.")


async def close_db():
    await engine.dispose()
    logger.info("Database connection closed.")
