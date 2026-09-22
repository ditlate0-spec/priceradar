"""
API истории пиков.
См. ТЗ 14.3.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.database import get_session_factory
from app.models.peaks import Peak

router = APIRouter(prefix="/api/v1/peaks", tags=["peaks"])


@router.get("")
async def list_peaks(
    pair: Optional[str] = Query(None, description="BTC/USDT"),
    exchange_pair: Optional[str] = Query(None, description="binance-bybit"),
    direction: Optional[str] = Query(None, description="binance→bybit"),
    threshold: Optional[float] = Query(None, description="0.3 / 0.5 / 1.0 / 2.0"),
    from_ts: Optional[datetime] = Query(None, alias="from", description="ISO 8601, UTC"),
    to_ts: Optional[datetime] = Query(None, alias="to", description="ISO 8601, UTC"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Список пиков с фильтрами и пагинацией.
    По умолчанию — за последние 24 часа.
    """
    # Дефолтный период — последние 24 часа
    if to_ts is None:
        to_ts = datetime.now(timezone.utc)
    if from_ts is None:
        from_ts = to_ts - timedelta(hours=24)

    factory = get_session_factory()
    async with factory() as session:
        # Собираем условия
        conditions = [
            Peak.time_start >= from_ts,
            Peak.time_start <= to_ts,
        ]

        if pair or exchange_pair or direction:
            # row_id = '{pair}|{exchange_pair}|{direction_arrow}'
            # Фронт шлёт direction через дефис ("binance-bybit"),
            # а в row_id он со стрелкой ("binance→bybit").
            if pair:
                conditions.append(Peak.row_id.like(f"{pair}|%"))
            if exchange_pair:
                conditions.append(Peak.row_id.like(f"%|{exchange_pair}|%"))
            if direction:
                arrow = _direction_dash_to_arrow(direction)
                conditions.append(Peak.row_id.like(f"%|{arrow}"))

        if threshold is not None:
            conditions.append(Peak.threshold == threshold)

        # Считаем total
        count_stmt = select(func.count()).select_from(Peak).where(*conditions)
        total = (await session.execute(count_stmt)).scalar_one()

        # Берём страницу
        stmt = (
            select(Peak)
            .where(*conditions)
            .order_by(Peak.time_start.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "from": from_ts.isoformat(),
        "to": to_ts.isoformat(),
        "peaks": [_peak_to_dict(p) for p in rows],
    }


def _peak_to_dict(p: Peak) -> dict:
    return {
        "id": p.id,
        "row_id": p.row_id,
        "threshold": float(p.threshold),
        "threshold_version": p.threshold_version,
        "fee_version": p.fee_version,
        "time_start": p.time_start.isoformat(),
        "time_end": p.time_end.isoformat() if p.time_end else None,
        "duration_seconds": p.duration_seconds,
        "duration_data_seconds": p.duration_data_seconds,
        "spread_max_abs": float(p.spread_max_abs),
        "spread_avg_abs": float(p.spread_avg_abs),
        "time_max": p.time_max.isoformat() if p.time_max else None,
        "is_paused": p.is_paused,
    }



def _direction_dash_to_arrow(direction: str) -> str:
    """
    Принимает 'binance-bybit', возвращает 'binance→bybit'.
    Если direction уже содержит стрелку — возвращает как есть.
    """
    if "→" in direction:
        return direction
    parts = direction.split("-")
    if len(parts) != 2:
        return direction
    return f"{parts[0]}→{parts[1]}"