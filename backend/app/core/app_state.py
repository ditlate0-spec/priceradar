"""
Глобальные синглтоны приложения.
Хранит ссылки на общие объекты, чтобы не плодить циклические импорты.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.core.buffer_manager import BufferManager
from app.core.store import PriceStore, price_store

class AppState:
    """Контейнер для синглтонов."""

    def __init__(self, price_store: PriceStore):
        self.price_store: PriceStore = price_store
        self.buffer_manager: BufferManager = BufferManager(capacity=3600)

        # Фоновые таски (заполняются в lifespan)
        self.tick_task = None
        self.aggregator_task = None
        self.peak_detector_task = None

        # Состояние агрегатора: последняя успешно записанная минута
        self.last_aggregated_minute = None

        # Состояние детектора пиков:
        # открытые пики: {(row_id, threshold): peak_id в БД}
        self.open_peaks: dict = {}
        # статистика по открытым пикам: {(row_id, threshold): {...}}
        self.peak_states: dict = {}

        self.started_at: Optional[datetime] = None
        self.last_aggregated_minute = None

app_state: Optional[AppState] = None


def init_app_state() -> AppState:
    """Инициализирует глобальное состояние. Вызывается один раз в lifespan."""
    global app_state
    if app_state is None:
        app_state = AppState(price_store=price_store)
    return app_state


def get_app_state() -> AppState:
    """Возвращает текущий AppState. Падает, если не инициализирован."""
    if app_state is None:
        raise RuntimeError("app_state не инициализирован — lifespan ещё не стартовал")
    return app_state