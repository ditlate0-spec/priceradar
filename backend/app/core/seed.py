"""
Наполнение таблицы exchange_fees начальными значениями.
Вызывается при старте приложения, если таблица пуста.
"""
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.exchange_fees import ExchangeFee


async def seed_exchange_fees(session: AsyncSession) -> None:
    """Если таблица exchange_fees пуста — заполняет дефолтными комиссиями."""
    count_stmt = select(func.count()).select_from(ExchangeFee)
    result = await session.execute(count_stmt)
    existing = result.scalar_one()

    if existing > 0:
        logger.info(f"exchange_fees already has {existing} rows, skipping seed")
        return

    settings = get_settings()
    now = datetime.now(timezone.utc)

    defaults = [
        ("binance", settings.fee_binance),
        ("bybit", settings.fee_bybit),
        ("okx", settings.fee_okx),
    ]

    for exchange, fee in defaults:
        session.add(
            ExchangeFee(
                exchange=exchange,
                taker_fee=fee,
                effective_from=now,
                effective_to=None,
                source="manual",
            )
        )

    await session.commit()
    logger.info(f"Seeded exchange_fees with {len(defaults)} rows")