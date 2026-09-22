"""
Отправка уведомлений в Telegram.
См. ТЗ 7.2 (v1.1, №12).

Токен и chat_id читаются из .env через настройки.
Rate limiting: не чаще чем TELEGRAM_COOLDOWN_MINUTES минут на ряд.
"""
from __future__ import annotations

import time
from typing import Optional

import httpx
from loguru import logger

from app.core.config import get_settings

# Простая in-memory карта: row_id -> timestamp последней отправки
_last_sent: dict[str, float] = {}


async def send_telegram(text: str) -> bool:
    """
    Отправляет текстовое сообщение в Telegram.
    Возвращает True при успехе, False при ошибке.
    """
    settings = get_settings()

    if not settings.telegram_enabled:
        logger.debug("notifier: TELEGRAM_ENABLED=false, пропускаем")
        return False

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("notifier: token или chat_id не заданы, пропускаем")
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(
                    "notifier: Telegram вернул {} — {}", resp.status_code, resp.text[:200]
                )
                return False
        logger.info("notifier: сообщение отправлено")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("notifier: ошибка отправки: {}", exc)
        return False


async def notify_peak_opened(
    row_id: str,
    threshold: float,
    spread_net: float,
    ts_iso: str,
) -> bool:
    """
    Уведомляет о новом открытом пике.
    Проверяет порог и cooldown.
    """
    settings = get_settings()

    # 1. Проверка порога
    if threshold < settings.telegram_min_threshold:
        logger.debug(
            "notifier: порог {} < {} — пропускаем", threshold, settings.telegram_min_threshold
        )
        return False

    # 2. Проверка cooldown
    now = time.monotonic()
    last = _last_sent.get(row_id, 0.0)
    cooldown_sec = settings.telegram_cooldown_minutes * 60
    if now - last < cooldown_sec:
        remaining = int(cooldown_sec - (now - last))
        logger.debug("notifier: cooldown для {}, осталось {} сек", row_id, remaining)
        return False

    # 3. Формируем текст
    parts = row_id.split("|")
    pair = parts[0] if len(parts) > 0 else row_id
    exchange_pair = parts[1] if len(parts) > 1 else "?"
    direction = parts[2] if len(parts) > 2 else "?"

    text = (
        f"⚠️ <b>Пик по {pair}</b>\n"
        f"Направление: <code>{direction}</code>\n"
        f"Порог: <b>{threshold:.2f}%</b>\n"
        f"Net: <b>{abs(spread_net):.4f}%</b>\n"
        f"Время (UTC): <code>{ts_iso[:19]}</code>"
    )

    # 4. Отправка
    sent = await send_telegram(text)
    if sent:
        _last_sent[row_id] = now
    return sent


async def send_test() -> bool:
    """Отправляет тестовое сообщение. Для проверки настройки."""
    text = "✅ <b>PriceRadar</b>: тестовое уведомление. Всё работает."
    return await send_telegram(text)