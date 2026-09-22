from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency для получения сессии БД."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Создать все таблицы и заполнить дефолтными комиссиями."""
    # Импорт моделей нужен, чтобы SQLAlchemy «увидел» их до create_all
    from app.models import exchange_fees       # noqa: F401
    from app.models import spread_aggregates   # noqa: F401
    from app.models import skipped_minutes     # noqa: F401
    from app.models import peaks               # noqa: F401
    from app.core.seed import seed_exchange_fees

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Заполняем exchange_fees дефолтными значениями, если таблица пуста
    factory = get_session_factory()
    async with factory() as session:
        await seed_exchange_fees(session)

    logger.info("Database initialized, tables created (if not existed)")


async def dispose_db() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")