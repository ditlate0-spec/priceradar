"""
API управления комиссиями.
См. ТЗ 14.6 и 7.2 (№17).

GET /api/v1/fees — активные комиссии на дату (или текущие)
POST /api/v1/fees — обновить комиссию биржи (создать новую версию)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from app.core.database import get_session_factory
from app.models.exchange_fees import ExchangeFee

router = APIRouter(prefix="/api/v1/fees", tags=["fees"])


class FeeUpdateRequest(BaseModel):
    exchange: str = Field(..., description="binance | bybit | okx")
    taker_fee: float = Field(..., ge=0, le=1, description="доля, например 0.001 = 0.1%")
    source: str = Field(default="manual")


@router.get("")
async def get_fees(
    at: Optional[datetime] = Query(None, description="ISO 8601 UTC; по умолчанию — сейчас"),
):
    """Активные комиссии на указанный момент."""
    at = at or datetime.now(timezone.utc)

    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(ExchangeFee)
            .where(ExchangeFee.effective_from <= at)
            .where(
                (ExchangeFee.effective_to.is_(None))
                | (ExchangeFee.effective_to > at)
            )
            .order_by(ExchangeFee.exchange, ExchangeFee.effective_from.desc())
        )
        rows = (await session.execute(stmt)).scalars().all()

    # последняя запись на биржу
    seen: dict[str, ExchangeFee] = {}
    for r in rows:
        if r.exchange not in seen:
            seen[r.exchange] = r

    return {
        "at": at.isoformat(),
        "fees": [
            {
                "exchange": r.exchange,
                "taker_fee": float(r.taker_fee),
                "source": r.source,
                "effective_from": r.effective_from.isoformat(),
                "effective_to": r.effective_to.isoformat() if r.effective_to else None,
            }
            for r in seen.values()
        ],
    }


@router.post("")
async def update_fee(req: FeeUpdateRequest):
    """
    Создаёт новую версию комиссии для биржи:
    - закрывает текущую (проставляет effective_to = now)
    - создаёт новую с effective_from = now
    """
    if req.exchange not in ("binance", "bybit", "okx"):
        raise HTTPException(status_code=400, detail="exchange должен быть binance | bybit | okx")

    now = datetime.now(timezone.utc)
    factory = get_session_factory()
    async with factory() as session:
        # закрываем текущую активную
        await session.execute(
            update(ExchangeFee)
            .where(ExchangeFee.exchange == req.exchange)
            .where(ExchangeFee.effective_to.is_(None))
            .values(effective_to=now)
        )

        # создаём новую
        session.add(
            ExchangeFee(
                exchange=req.exchange,
                taker_fee=req.taker_fee,
                effective_from=now,
                effective_to=None,
                source=req.source,
            )
        )
        await session.commit()

    return {
        "status": "ok",
        "exchange": req.exchange,
        "taker_fee": req.taker_fee,
        "effective_from": now.isoformat(),
    }