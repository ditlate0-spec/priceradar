"""
Фоновый таск: раз в секунду считает все спреды и складывает в ring-буферы.
См. ТЗ 8.4 — секундный буфер (in-memory).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger

from app.core.app_state import AppState
from app.core.spread_engine import compute_all_spreads
from app.core.store import MVP_PAIRS

TICK_INTERVAL_SECONDS = 1.0


async def tick_loop(state: AppState) -> None:
    """Бесконечный цикл: раз в секунду считает спреды и пишет в буферы."""
    logger.info("tick_processor: старт, интервал {} сек", TICK_INTERVAL_SECONDS)

    while True:
        tick_started = datetime.now(timezone.utc)
        try:
            _process_one_tick(state)
        except Exception as exc:  # noqa: BLE001
            logger.exception("tick_processor: ошибка в тике: {}", exc)

        elapsed = (datetime.now(timezone.utc) - tick_started).total_seconds()
        sleep_for = max(0.0, TICK_INTERVAL_SECONDS - elapsed)
        try:
            await asyncio.sleep(sleep_for)
        except asyncio.CancelledError:
            logger.info("tick_processor: остановлен")
            raise


def _process_one_tick(state: AppState) -> None:
    """Один тик: считаем спреды, пишем в буферы."""
    ts = datetime.now(timezone.utc)

    rows = compute_all_spreads(store=state.price_store, pairs=MVP_PAIRS)

    for row in rows:
        buf = state.buffer_manager.get(row.row_id)
        if buf is None:
            buf = state.buffer_manager.register(row.row_id)
        buf.add(spread_net=row.spread_net, spread_gross=row.spread_gross, ts=ts)