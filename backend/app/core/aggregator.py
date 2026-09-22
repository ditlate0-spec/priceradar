"""
Минутный агрегатор.
Раз в минуту читает последние 60 секундных точек каждого буфера
и пишет агрегат в БД.

См. ТЗ 8.5, 8.6, 10.2.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.app_state import AppState
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.fees import compute_fee_version
from app.core.ring_buffer import SpreadPoint
from app.models.skipped_minutes import SkippedMinute
from app.models.spread_aggregates import SpreadAggregate

SAMPLES_PER_MINUTE = 60

COUNTER_THRESHOLDS: list[tuple[str, float]] = [
    ("seconds_above_03", 0.3),
    ("seconds_above_05", 0.5),
    ("seconds_above_10", 1.0),
    ("seconds_above_20", 2.0),
]


def _minute_floor(ts: datetime) -> datetime:
    return ts.replace(second=0, microsecond=0)


def _one_minute() -> timedelta:
    return timedelta(minutes=1)


async def aggregator_loop(state: AppState) -> None:
    """Бесконечный цикл: спим до начала следующей минуты, агрегируем прошедшую."""
    logger.info("aggregator: старт")

    while True:
        now = datetime.now(timezone.utc)
        seconds_to_next_minute = 60 - now.second - now.microsecond / 1_000_000

        try:
            # +0.5 сек «подушки», чтобы не проснуться до фактической минуты
            await asyncio.sleep(seconds_to_next_minute + 0.5)
        except asyncio.CancelledError:
            logger.info("aggregator: остановлен во время sleep")
            raise

        # Целевая минута — та, что уже завершилась
        minute_ts = _minute_floor(datetime.now(timezone.utc)) - _one_minute()

        # Защита от повторной записи той же минуты
        if state.last_aggregated_minute is not None and minute_ts <= state.last_aggregated_minute:
            logger.debug(
                "aggregator: минута {} уже записана, пропускаем",
                minute_ts.isoformat(),
            )
            continue

        try:
            written, skipped = await _aggregate_minute(state, minute_ts)
            state.last_aggregated_minute = minute_ts
            logger.info(
                "aggregator: минута {} — записано {}, пропущено {}",
                minute_ts.isoformat(), written, skipped,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "aggregator: ошибка при агрегации минуты {}: {}",
                minute_ts, exc,
            )
            # Не обновляем last_aggregated_minute — попробуем снова в след. цикле


async def _aggregate_minute(state: AppState, minute_ts: datetime) -> tuple[int, int]:
    """Агрегирует одну минуту по всем row_id. Возвращает (записано, пропущено)."""
    settings = get_settings()
    bm = state.buffer_manager

    factory = get_session_factory()
    written = 0
    skipped = 0
    now = datetime.now(timezone.utc)

    async with factory() as session:
        fee_version_cache: dict[tuple[str, str], str] = {}

        for row_id in bm.all_row_ids():
            buf = bm.get(row_id)
            if buf is None:
                continue

            points = [
                p for p in buf.get_last_n(SAMPLES_PER_MINUTE * 3)
                if _minute_floor(p.ts) == minute_ts
            ]

            if not points:
                await _upsert_skipped(session, row_id, minute_ts, "exchange_down", now)
                skipped += 1
                continue

            agg = _build_aggregate(row_id, minute_ts, points, settings)
            if agg is None:
                await _upsert_skipped(session, row_id, minute_ts, "exchange_down", now)
                skipped += 1
                continue

            ex_a, ex_b = _parse_exchanges(row_id)
            key = (ex_a, ex_b)
            if key not in fee_version_cache:
                fee_version_cache[key] = await compute_fee_version(
                    session, ex_a, ex_b, at=minute_ts
                )
            agg.fee_version = fee_version_cache[key]

            await _upsert_aggregate(session, agg)
            written += 1

        await session.commit()

    return written, skipped


async def _upsert_aggregate(session, agg: SpreadAggregate) -> None:
    """INSERT ... ON CONFLICT DO NOTHING — защита от повторной записи."""
    values = {
        "row_id": agg.row_id,
        "minute_ts": agg.minute_ts,
        "spread_min": agg.spread_min,
        "spread_max": agg.spread_max,
        "spread_avg_abs": agg.spread_avg_abs,
        "spread_avg_signed": agg.spread_avg_signed,
        "spread_last": agg.spread_last,
        "spread_gross_min": agg.spread_gross_min,
        "spread_gross_max": agg.spread_gross_max,
        "spread_gross_avg_abs": agg.spread_gross_avg_abs,
        "spread_gross_last": agg.spread_gross_last,
        "seconds_above_03": agg.seconds_above_03,
        "seconds_above_05": agg.seconds_above_05,
        "seconds_above_10": agg.seconds_above_10,
        "seconds_above_20": agg.seconds_above_20,
        "sample_count": agg.sample_count,
        "partial": agg.partial,
        "stale_level": agg.stale_level,
        "threshold_version": agg.threshold_version,
        "fee_version": agg.fee_version,
    }
    stmt = pg_insert(SpreadAggregate).values(**values).on_conflict_do_nothing(
        constraint="uq_aggregate_row_minute"
    )
    await session.execute(stmt)


async def _upsert_skipped(session, row_id: str, minute_ts: datetime,
                          reason: str, now: datetime) -> None:
    """INSERT ... ON CONFLICT DO NOTHING для skipped_minutes."""
    values = {
        "row_id": row_id,
        "minute_ts": minute_ts,
        "reason": reason,
        "detected_at": now,
    }
    stmt = pg_insert(SkippedMinute).values(**values).on_conflict_do_nothing()
    await session.execute(stmt)


def _parse_exchanges(row_id: str) -> tuple[str, str]:
    """row_id = '{pair}|{ex_a}-{ex_b}|{direction}' -> (ex_a, ex_b)."""
    parts = row_id.split("|")
    exchange_pair = parts[1]
    a, b = exchange_pair.split("-", 1)
    return a, b


def _build_aggregate(
    row_id: str,
    minute_ts: datetime,
    points: list[SpreadPoint],
    settings,
) -> SpreadAggregate | None:
    """Собирает SpreadAggregate из списка точек. None, если все точки пустые."""
    nets = [p.spread_net for p in points if p.spread_net is not None]
    grosses = [p.spread_gross for p in points if p.spread_gross is not None]

    if not nets:
        return None

    sample_count = len(points)
    data_count = len(nets)

    # Net-метрики (основные)
    spread_min = min(nets)
    spread_max = max(nets)
    spread_avg_abs = sum(abs(x) for x in nets) / data_count
    spread_avg_signed = sum(nets) / data_count
    spread_last = nets[-1]

    # Gross-метрики (для переключателя net/gross)
    if grosses:
        gross_min = min(grosses)
        gross_max = max(grosses)
        gross_avg_abs = sum(abs(x) for x in grosses) / len(grosses)
        gross_last = grosses[-1]
    else:
        gross_min = None
        gross_max = None
        gross_avg_abs = None
        gross_last = None

    counters = {name: 0 for name, _ in COUNTER_THRESHOLDS}
    for x in nets:
        for name, thr in COUNTER_THRESHOLDS:
            if abs(x) >= thr:
                counters[name] += 1

    partial = sample_count < SAMPLES_PER_MINUTE
    stale_level = "ok" if not partial else "stale"

    return SpreadAggregate(
        row_id=row_id,
        minute_ts=minute_ts,
        spread_min=spread_min,
        spread_max=spread_max,
        spread_avg_abs=spread_avg_abs,
        spread_avg_signed=spread_avg_signed,
        spread_last=spread_last,
        spread_gross_min=gross_min,
        spread_gross_max=gross_max,
        spread_gross_avg_abs=gross_avg_abs,
        spread_gross_last=gross_last,
        seconds_above_03=counters["seconds_above_03"],
        seconds_above_05=counters["seconds_above_05"],
        seconds_above_10=counters["seconds_above_10"],
        seconds_above_20=counters["seconds_above_20"],
        sample_count=sample_count,
        partial=partial,
        stale_level=stale_level,
        threshold_version=settings.threshold_version,
        fee_version="__pending__",
    )