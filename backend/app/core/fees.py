"""
Работа с комиссиями и fee_version.

fee_version — детерминированная строка формата:
    fees_<YYYY_MM>_<YYYY_MM>
где первая дата — активная версия комиссии биржи A, вторая — биржи B.

Смена комиссии у одной биржи меняет fee_version у всех рядов с её участием
(см. ТЗ 8.2).
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.exchange_fees import ExchangeFee


def _format_yyyymm(dt: datetime) -> str:
    return dt.strftime("%Y_%m")


async def get_active_fee(
    session: AsyncSession,
    exchange: str,
    at: datetime | None = None,
) -> float:
    """
    Возвращает активную taker-комиссию биржи на указанный момент.
    Если запись не найдена — возвращает значение из .env по умолчанию.
    """
    at = at or datetime.now(timezone.utc)

    stmt = (
        select(ExchangeFee)
        .where(ExchangeFee.exchange == exchange)
        .where(ExchangeFee.effective_from <= at)
        .where(
            (ExchangeFee.effective_to.is_(None))
            | (ExchangeFee.effective_to > at)
        )
        .order_by(ExchangeFee.effective_from.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        # fallback — из конфига
        settings = get_settings()
        fallback = {
            "binance": settings.fee_binance,
            "bybit": settings.fee_bybit,
            "okx": settings.fee_okx,
        }
        return fallback.get(exchange.lower(), 0.001)

    return float(row.taker_fee)


async def compute_fee_version(
    session: AsyncSession,
    exchange_a: str,
    exchange_b: str,
    at: datetime | None = None,
) -> str:
    """
    Вычисляет fee_version для пары бирж (A, B) на момент `at`.
    Формат: fees_<YYYY_MM>_<YYYY_MM>
    """
    at = at or datetime.now(timezone.utc)

    async def _effective_from(exchange: str) -> datetime:
        stmt = (
            select(ExchangeFee.effective_from)
            .where(ExchangeFee.exchange == exchange)
            .where(ExchangeFee.effective_from <= at)
            .where(
                (ExchangeFee.effective_to.is_(None))
                | (ExchangeFee.effective_to > at)
            )
            .order_by(ExchangeFee.effective_from.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        dt = result.scalar_one_or_none()
        # если записи нет — используем «сейчас», чтобы fee_version не был пустым
        return dt or at

    from_a = await _effective_from(exchange_a)
    from_b = await _effective_from(exchange_b)

    return f"fees_{_format_yyyymm(from_a)}_{_format_yyyymm(from_b)}"