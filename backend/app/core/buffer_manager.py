"""
Менеджер ring-буферов: один буфер на каждый ряд.
Ряд = pair + exchange_pair + direction.
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional

from app.core.ring_buffer import RingBuffer


def make_row_id(pair: str, exchange_a: str, exchange_b: str, direction: str) -> str:
    """
    Формирует row_id в том же формате, что SpreadRow.row_id:
        {pair}|{exchange_a}-{exchange_b}|{direction}
    Пример:
        BTC/USDT|binance-bybit|binance→bybit
    """
    return f"{pair}|{exchange_a}-{exchange_b}|{direction}"


class BufferManager:
    """Хранит RingBuffer по каждому row_id."""

    def __init__(self, capacity: int = 3600):
        self._capacity = capacity
        self._buffers: Dict[str, RingBuffer] = {}

    def register(self, row_id: str) -> RingBuffer:
        """Создать буфер для ряда (идемпотентно)."""
        if row_id not in self._buffers:
            self._buffers[row_id] = RingBuffer(capacity=self._capacity)
        return self._buffers[row_id]

    def register_many(self, row_ids: Iterable[str]) -> None:
        for rid in row_ids:
            self.register(rid)

    def get(self, row_id: str) -> Optional[RingBuffer]:
        return self._buffers.get(row_id)

    def all_row_ids(self) -> list[str]:
        return list(self._buffers.keys())

    def is_ready(self, min_points: int = 300) -> bool:
        """Готовы ли ВСЕ буферы (используется для /health)."""
        if not self._buffers:
            return False
        return all(b.is_ready(min_points) for b in self._buffers.values())

    def min_size(self) -> int:
        """Минимальный размер среди всех буферов (для buffer_eta)."""
        if not self._buffers:
            return 0
        return min(len(b) for b in self._buffers.values())