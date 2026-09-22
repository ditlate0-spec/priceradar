"""
Секундный ring buffer для хранения значений спреда.
Один буфер на один ряд (pair + exchange_pair + direction).
Хранит 3600 точек (1 час), в БД не пишется.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Optional, NamedTuple


class SpreadPoint(NamedTuple):
    """Одна секундная точка."""
    ts: datetime
    spread_net: Optional[float]
    spread_gross: Optional[float]


class RingBuffer:
    """Ring buffer на 3600 секундных точек."""

    def __init__(self, capacity: int = 3600):
        self._capacity = capacity
        self._buffer: deque[SpreadPoint] = deque(maxlen=capacity)

    def add(self, spread_net: Optional[float], spread_gross: Optional[float],
            ts: Optional[datetime] = None) -> None:
        if ts is None:
            ts = datetime.now(timezone.utc)
        self._buffer.append(SpreadPoint(ts=ts, spread_net=spread_net, spread_gross=spread_gross))

    def get_latest(self) -> Optional[SpreadPoint]:
        return self._buffer[-1] if self._buffer else None

    def get_last_n(self, n: int) -> list[SpreadPoint]:
        if n <= 0:
            return []
        return list(self._buffer)[-n:]

    def is_ready(self, min_points: int = 300) -> bool:
        return len(self._buffer) >= min_points

    def __len__(self) -> int:
        return len(self._buffer)

    @property
    def capacity(self) -> int:
        return self._capacity