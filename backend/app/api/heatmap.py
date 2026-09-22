"""
API тепловой карты.
См. ТЗ 14.4.

GET /api/v1/heatmap
  ?pair=BTC/USDT                  (обязательно)
  &exchange_pair=binance-okx       (обязательно)
  &direction=binance-okx           (обязательно)
  &days=7                          (по умолчанию 7, максимум 90)
  &tz=utc|local                    (по умолчанию utc)
  &metric=pct_above_03|avg_spread  (по умолчанию pct_above_03)

Возвращает 24 ячейки (по часам суток).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.database import get_session_factory
from app.models.spread_aggregates import SpreadAggregate

router = APIRouter(prefix="/api/v1/heatmap", tags=["heatmap"])


def _direction_dash_to_arrow(direction: str) -> str:
    parts = direction.split("-")
    if len(parts) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"direction должен быть в формате 'exchange_a-exchange_b', получено: {direction!r}",
        )
    return f"{parts[0]}→{parts[1]}"


def _build_row_id(pair: str, exchange_pair: str, direction: str) -> str:
    arrow = _direction_dash_to_arrow(direction)
    return f"{pair}|{exchange_pair}|{arrow}"


@router.get("")
async def heatmap(
    pair: str = Query(..., description="BTC/USDT"),
    exchange_pair: str = Query(..., description="binance-okx"),
    direction: str = Query(..., description="binance-okx"),
    days: int = Query(7, ge=1, le=90),
    tz: str = Query("utc", description="utc / local"),
    metric: str = Query("pct_above_03", description="pct_above_03 / avg_spread"),
):
    if tz not in ("utc", "local"):
        raise HTTPException(status_code=400, detail="tz должен быть 'utc' или 'local'")
    if metric not in ("pct_above_03", "avg_spread"):
        raise HTTPException(
            status_code=400,
            detail="metric должен быть 'pct_above_03' или 'avg_spread'",
        )

    row_id = _build_row_id(pair, exchange_pair, direction)

    to_ts = datetime.now(timezone.utc)
    from_ts = to_ts - timedelta(days=days)

    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                select(SpreadAggregate)
                .where(
                    SpreadAggregate.row_id == row_id,
                    SpreadAggregate.minute_ts >= from_ts,
                    SpreadAggregate.minute_ts <= to_ts,
                )
                .order_by(SpreadAggregate.minute_ts)
            )
        ).scalars().all()

    # Агрегируем по часам суток
    cells = _aggregate_by_hour(rows, tz=tz)

    return {
        "row_id": row_id,
        "days": days,
        "tz": tz,
        "metric": metric,
        "from": from_ts.isoformat(),
        "to": to_ts.isoformat(),
        "threshold_version": rows[0].threshold_version if rows else None,
        "fee_version": rows[0].fee_version if rows else None,
        "cells": cells,
    }


def _aggregate_by_hour(rows: list[SpreadAggregate], tz: str) -> list[dict]:
    """
    Собирает 24 ячейки — по одной на каждый час суток.
    Для tz=local конвертирует в локальный пояс сервера.
    """
    buckets: dict[int, dict] = {
        h: {
            "hour": h,
            "total_seconds": 0,
            "seconds_above_03": 0,
            "seconds_above_05": 0,
            "seconds_above_10": 0,
            "seconds_above_20": 0,
            "sum_abs": 0.0,
            "weight": 0,
            "max_abs": 0.0,
            "samples": 0,
        }
        for h in range(24)
    }

    for r in rows:
        ts = r.minute_ts
        if tz == "local":
            # Локальный пояс сервера — простая конвертация
            ts = ts.astimezone()
        hour = ts.hour

        b = buckets[hour]
        b["total_seconds"] += r.sample_count
        b["seconds_above_03"] += r.seconds_above_03
        b["seconds_above_05"] += r.seconds_above_05
        b["seconds_above_10"] += r.seconds_above_10
        b["seconds_above_20"] += r.seconds_above_20

        if r.spread_avg_abs is not None:
            b["sum_abs"] += float(r.spread_avg_abs) * r.sample_count
            b["weight"] += r.sample_count

        if r.spread_max is not None:
            b["max_abs"] = max(b["max_abs"], abs(float(r.spread_max)))

        b["samples"] += 1

    out: list[dict] = []
    for h in range(24):
        b = buckets[h]
        total = b["total_seconds"]
        if total == 0:
            out.append({
                "hour": h,
                "total_seconds": 0,
                "pct_above_03": None,
                "pct_above_05": None,
                "pct_above_10": None,
                "pct_above_20": None,
                "avg_spread_abs": None,
                "max_abs": None,
                "no_data": True,
            })
            continue

        out.append({
            "hour": h,
            "total_seconds": total,
            "pct_above_03": round(b["seconds_above_03"] / total * 100, 2),
            "pct_above_05": round(b["seconds_above_05"] / total * 100, 2),
            "pct_above_10": round(b["seconds_above_10"] / total * 100, 2),
            "pct_above_20": round(b["seconds_above_20"] / total * 100, 2),
            "avg_spread_abs": (
                round(b["sum_abs"] / b["weight"], 6) if b["weight"] > 0 else None
            ),
            "max_abs": round(b["max_abs"], 6),
            "no_data": False,
        })

    return out