"""
API истории спредов.
См. ТЗ 14.2.

GET /api/v1/spreads/history
  ?pair=BTC/USDT                  (обязательно)
  &exchange_pair=binance-okx       (обязательно, через дефис)
  &direction=binance-okx           (обязательно, через дефис — куда движемся)
  &from=...&to=...                 (по умолчанию 24 часа)
  &interval=1m|5m|15m|1h|1d        (по умолчанию 1m)
  &metric=net|gross                (по умолчанию net)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.core.database import get_session_factory
from app.models.spread_aggregates import SpreadAggregate

router = APIRouter(prefix="/api/v1/spreads", tags=["spreads"])


# Поддерживаемые интервалы → размер в минутах
INTERVAL_MINUTES: dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "1d": 1440,
}


def _direction_dash_to_arrow(direction: str) -> str:
    """
    Принимает 'binance-okx', возвращает 'binance→okx'.
    Пользователь не должен возиться с URL-encoded стрелкой.
    """
    parts = direction.split("-")
    if len(parts) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"direction должен быть в формате 'exchange_a-exchange_b', получено: {direction!r}",
        )
    return f"{parts[0]}→{parts[1]}"


def _build_row_id(pair: str, exchange_pair: str, direction: str) -> str:
    """
    row_id = '{pair}|{exchange_pair}|{direction_arrow}'
    Пример: BTC/USDT|binance-okx|binance→okx
    """
    arrow = _direction_dash_to_arrow(direction)
    return f"{pair}|{exchange_pair}|{arrow}"


@router.get("/history")
async def spreads_history(
    pair: str = Query(..., description="BTC/USDT"),
    exchange_pair: str = Query(..., description="binance-okx"),
    direction: str = Query(..., description="binance-okx (куда движемся)"),
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
    interval: str = Query("1m", description="1m / 5m / 15m / 1h / 1d"),
    metric: str = Query("net", description="net / gross"),
):
    # Проверки
    if interval not in INTERVAL_MINUTES:
        raise HTTPException(
            status_code=400,
            detail=f"interval должен быть одним из {list(INTERVAL_MINUTES)}",
        )
    if metric not in ("net", "gross"):
        raise HTTPException(
            status_code=400,
            detail="metric должен быть 'net' или 'gross'",
        )

    row_id = _build_row_id(pair, exchange_pair, direction)

    if to_ts is None:
        to_ts = datetime.now(timezone.utc)
    if from_ts is None:
        from_ts = to_ts - timedelta(hours=24)

    # Проверка на 90-дневный лимит (ТЗ 11)
    if (to_ts - from_ts).days > 90:
        raise HTTPException(
            status_code=400,
            detail="Максимальный диапазон from/to — 90 дней",
        )

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

    if not rows:
        return {
            "row_id": row_id,
            "from": from_ts.isoformat(),
            "to": to_ts.isoformat(),
            "interval": interval,
            "metric": metric,
            "threshold_version": None,
            "fee_version": None,
            "summary": None,
            "points": [],
            "partial": True,
            "note": "Нет данных за указанный период",
        }

    # Группируем по интервалу
    grouped = _group_by_interval(rows, INTERVAL_MINUTES[interval])
    points = [_bucket_to_point(b, metric) for b in grouped]

    summary = _build_summary(grouped, metric)
    threshold_version = rows[0].threshold_version
    fee_version = rows[0].fee_version

    return {
        "row_id": row_id,
        "from": from_ts.isoformat(),
        "to": to_ts.isoformat(),
        "interval": interval,
        "metric": metric,
        "threshold_version": threshold_version,
        "fee_version": fee_version,
        "summary": summary,
        "points": points,
    }


def _group_by_interval(
    rows: list[SpreadAggregate], minutes: int
) -> list[list[SpreadAggregate]]:
    """
    Группирует строки в бакеты по `minutes` минут.
    Ключ бакета — минута, округлённая вниз до кратного `minutes`.

    Пример: interval=5m, minute_ts=13:42 → bucket=13:40.
    """
    if minutes <= 1:
        # Быстрый путь — каждая строка = свой бакет
        return [[r] for r in rows]

    buckets: dict[datetime, list[SpreadAggregate]] = {}
    for r in rows:
        bucket_key = _bucket_ts(r.minute_ts, minutes)
        buckets.setdefault(bucket_key, []).append(r)

    # Возвращаем в хронологическом порядке
    return [buckets[k] for k in sorted(buckets)]


def _bucket_ts(ts: datetime, minutes: int) -> datetime:
    """Округляет ts вниз до кратного `minutes` минут от начала суток."""
    total_minutes = ts.hour * 60 + ts.minute
    floored = (total_minutes // minutes) * minutes
    return ts.replace(
        hour=floored // 60,
        minute=floored % 60,
        second=0,
        microsecond=0,
    )


def _bucket_to_point(
    bucket: list[SpreadAggregate], metric: str
) -> dict:
    """
    Собирает один point из бакета минутных агрегатов.
    Для metric=net используется spread_*.
    Для metric=gross — spread_gross_*.
    """
    if metric == "net":
        keys = ("spread_min", "spread_max", "spread_avg_abs", "spread_avg_signed", "spread_last")
    else:
        keys = ("spread_gross_min", "spread_gross_max", "spread_gross_avg_abs", None, "spread_gross_last")

    def col(r, name):
        if name is None:
            return None
        return getattr(r, name)

    # Для avg_abs — взвешенное по sample_count
    total_samples = sum(r.sample_count for r in bucket)

    def weighted_avg(field: str):
        total = 0.0
        wsum = 0
        for r in bucket:
            v = getattr(r, field)
            if v is None:
                continue
            total += float(v) * r.sample_count
            wsum += r.sample_count
        return (total / wsum) if wsum > 0 else None

    def min_of(field: str):
        vals = [float(getattr(r, field)) for r in bucket if getattr(r, field) is not None]
        return min(vals) if vals else None

    def max_of(field: str):
        vals = [float(getattr(r, field)) for r in bucket if getattr(r, field) is not None]
        return max(vals) if vals else None

    def last_of(field: str):
        # последняя запись бакета
        for r in reversed(bucket):
            v = getattr(r, field)
            if v is not None:
                return float(v)
        return None

    min_key, max_key, avg_key, signed_key, last_key = keys

    return {
        "ts": _bucket_ts(bucket[0].minute_ts, 1).isoformat(),  # ts первой минуты бакета
        "min": min_of(min_key) if min_key else None,
        "max": max_of(max_key) if max_key else None,
        "avg_abs": weighted_avg(avg_key) if avg_key else None,
        "avg_signed": weighted_avg(signed_key) if signed_key else None,
        "last": last_of(last_key) if last_key else None,
        "seconds_above_03": sum(r.seconds_above_03 for r in bucket),
        "seconds_above_05": sum(r.seconds_above_05 for r in bucket),
        "seconds_above_10": sum(r.seconds_above_10 for r in bucket),
        "seconds_above_20": sum(r.seconds_above_20 for r in bucket),
        "sample_count": total_samples,
        "partial": any(r.partial for r in bucket),
    }


def _build_summary(buckets: list[list[SpreadAggregate]], metric: str) -> dict:
    """Сводка за весь период: средние, максимум, % времени выше порогов."""
    if metric == "net":
        avg_abs_field = "spread_avg_abs"
        avg_signed_field = "spread_avg_signed"
        max_field = "spread_max"
    else:
        avg_abs_field = "spread_gross_avg_abs"
        avg_signed_field = None
        max_field = "spread_gross_max"

    # Взвешенное среднее
    total_abs = 0.0
    total_signed = 0.0
    total_weight = 0
    max_abs = 0.0
    total_seconds = 0
    seconds_03 = seconds_05 = seconds_10 = seconds_20 = 0

    for bucket in buckets:
        for r in bucket:
            w = r.sample_count
            v_abs = getattr(r, avg_abs_field)
            if v_abs is not None:
                total_abs += float(v_abs) * w
                total_weight += w

            if avg_signed_field:
                v_signed = getattr(r, avg_signed_field)
                if v_signed is not None:
                    total_signed += float(v_signed) * w

            v_max = getattr(r, max_field)
            if v_max is not None:
                max_abs = max(max_abs, abs(float(v_max)))

            total_seconds += r.sample_count
            seconds_03 += r.seconds_above_03
            seconds_05 += r.seconds_above_05
            seconds_10 += r.seconds_above_10
            seconds_20 += r.seconds_above_20

    def pct(sec: int) -> float:
        return (sec / total_seconds * 100) if total_seconds > 0 else 0.0

    return {
        "spread_avg_abs": (total_abs / total_weight) if total_weight > 0 else None,
        "spread_avg_signed": (total_signed / total_weight) if total_weight > 0 else None,
        "spread_max_abs": max_abs,
        "total_samples": total_seconds,
        "pct_above_03": round(pct(seconds_03), 2),
        "pct_above_05": round(pct(seconds_05), 2),
        "pct_above_10": round(pct(seconds_10), 2),
        "pct_above_20": round(pct(seconds_20), 2),
    }