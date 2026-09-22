"""
Детектор пиков.
Раз в секунду проверяет все буферы, открывает/закрывает пики.

См. ТЗ 10.3:
- Открытие: |spread_net| >= порог пика впервые.
- Закрытие: |spread_net| < порог 3 секунды подряд (гистерезис).
- Пауза: пропуск данных — is_paused=True, гистерезис не отсчитывается.
- Пороги независимы: пики по разным порогам не мешают друг другу.

Статистика (sum_abs, data_count, max_abs) обновляется ТОЛЬКО когда
спред выше порога. Секунды гистерезиса (когда спред упал ниже)
не учитываются — они нужны только для закрытия пика.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger

from app.core.app_state import AppState
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.fees import compute_fee_version
from app.models.peaks import Peak

# Пороги пиков/счётчиков — ТЗ 6.1, раздел 9.2
DEFAULT_PEAK_THRESHOLDS: list[float] = [0.3, 0.5, 1.0, 2.0]

# Гистерезис: сколько секунд подряд ниже порога — закрываем пик (ТЗ 10.3)
HYSTERESIS_SECONDS = 3

# Как часто проверяем
CHECK_INTERVAL_SECONDS = 1.0


async def peak_detector_loop(state: AppState) -> None:
    """Бесконечный цикл: раз в секунду проверяет буферы на пики."""
    logger.info("peak_detector: старт")

    settings = get_settings()
    thresholds = DEFAULT_PEAK_THRESHOLDS

    while True:
        tick_started = datetime.now(timezone.utc)
        try:
            await _check_once(state, thresholds, settings)
        except Exception as exc:  # noqa: BLE001
            logger.exception("peak_detector: ошибка в тике: {}", exc)

        elapsed = (datetime.now(timezone.utc) - tick_started).total_seconds()
        sleep_for = max(0.0, CHECK_INTERVAL_SECONDS - elapsed)
        try:
            await asyncio.sleep(sleep_for)
        except asyncio.CancelledError:
            logger.info("peak_detector: остановлен")
            raise


async def _check_once(state: AppState, thresholds: list[float], settings) -> None:
    """Одна итерация: проверяем все буферы по всем порогам."""
    bm = state.buffer_manager
    factory = get_session_factory()

    async with factory() as session:
        for row_id in bm.all_row_ids():
            buf = bm.get(row_id)
            if buf is None:
                continue

            latest = buf.get_latest()
            if latest is None or latest.spread_net is None:
                # Пропуск данных — открытые пики идут в паузу
                for thr in thresholds:
                    key = (row_id, thr)
                    peak_id = state.open_peaks.get(key)
                    if peak_id is not None:
                        await _mark_paused(session, peak_id)
                continue

            value = latest.spread_net

            for thr in thresholds:
                await _process_threshold(
                    session=session,
                    state=state,
                    row_id=row_id,
                    thr=thr,
                    value=value,
                    ts=latest.ts,
                    settings=settings,
                )

        await session.commit()


async def _process_threshold(
    session,
    state: AppState,
    row_id: str,
    thr: float,
    value: float,
    ts: datetime,
    settings,
) -> None:
    """Обрабатывает один порог для одного row_id на одной точке."""
    key = (row_id, thr)
    abs_v = abs(value)
    above = abs_v >= thr

    peak_id = state.open_peaks.get(key)

    if peak_id is None:
        # Пик не открыт. Открываем, если превышен порог.
        if not above:
            return

        ex_a, ex_b = _parse_exchanges(row_id)
        fee_version = await compute_fee_version(session, ex_a, ex_b, at=ts)

        new_peak = Peak(
            row_id=row_id,
            threshold=thr,
            threshold_version=settings.threshold_version,
            fee_version=fee_version,
            time_start=ts,
            time_end=None,
            duration_seconds=None,
            duration_data_seconds=1,
            spread_max_abs=abs_v,
            spread_avg_abs=abs_v,
            time_max=ts,
            sum_abs=abs_v,
            is_paused=False,
        )
        session.add(new_peak)
        await session.flush()  # получить id

        state.open_peaks[key] = new_peak.id
        state.peak_states[key] = {
            "below_count": 0,
            "sum_abs": abs_v,
            "data_count": 1,
            "max_abs": abs_v,
            "time_max": ts,
            "time_start": ts,
        }
        logger.debug("peak_detector: открыт пик {} thr={}", row_id, thr)

        # Telegram-уведомление (ТЗ 7.2, v1.1)
        try:
            from app.core.notifier import notify_peak_opened
            await notify_peak_opened(
                row_id=row_id,
                threshold=thr,
                spread_net=value,
                ts_iso=ts.isoformat(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("notifier: не удалось отправить уведомление: {}", exc)

        return

    # Пик открыт. Обновляем статистику ТОЛЬКО когда спред выше порога.
    peak_state = state.peak_states.get(key)
    if peak_state is None:
        # На случай рассогласования — инициализируем
        peak_state = {
            "below_count": 0,
            "sum_abs": abs_v,
            "data_count": 1,
            "max_abs": abs_v,
            "time_max": ts,
            "time_start": ts,
        }
        state.peak_states[key] = peak_state
        return

    if above:
        # Спред выше порога — пик активен, обновляем статистику
        peak_state["sum_abs"] += abs_v
        peak_state["data_count"] += 1
        peak_state["below_count"] = 0

        if abs_v > peak_state["max_abs"]:
            peak_state["max_abs"] = abs_v
            peak_state["time_max"] = ts
    else:
        # Спред ниже порога — считаем гистерезис, статистику не трогаем
        peak_state["below_count"] += 1
        if peak_state["below_count"] >= HYSTERESIS_SECONDS:
            await _close_peak(session, peak_id, peak_state, ts)
            state.open_peaks.pop(key, None)
            state.peak_states.pop(key, None)
            logger.debug("peak_detector: закрыт пик {} thr={}", row_id, thr)


async def _mark_paused(session, peak_id: int) -> None:
    """Помечает открытый пик как is_paused=True."""
    peak = await session.get(Peak, peak_id)
    if peak is not None and not peak.is_paused:
        peak.is_paused = True


async def _close_peak(session, peak_id: int, peak_state: dict, end_ts: datetime) -> None:
    """Закрывает пик: проставляет time_end, duration_*, avg."""
    peak = await session.get(Peak, peak_id)
    if peak is None:
        return

    start = peak_state["time_start"]
    peak.time_end = end_ts
    peak.duration_seconds = int((end_ts - start).total_seconds())
    peak.duration_data_seconds = peak_state["data_count"]
    peak.spread_max_abs = peak_state["max_abs"]
    peak.spread_avg_abs = (
        peak_state["sum_abs"] / peak_state["data_count"]
        if peak_state["data_count"] > 0 else 0.0
    )
    peak.time_max = peak_state["time_max"]
    peak.sum_abs = peak_state["sum_abs"]
    peak.is_paused = False


def _parse_exchanges(row_id: str) -> tuple[str, str]:
    """row_id = '{pair}|{ex_a}-{ex_b}|{direction}' -> (ex_a, ex_b)."""
    parts = row_id.split("|")
    exchange_pair = parts[1]
    a, b = exchange_pair.split("-", 1)
    return a, b