"""
In-memory хранилище последних цен с бирж.

См. ТЗ 8.1:
- хранит bid/ask/last
- максимальный возраст данных — 5 секунд
- если старше — пометка stale_level = stale
- если биржа не отвечала всю минуту — unavailable
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Literal

StaleLevel = Literal["ok", "stale", "unavailable"]

# ТЗ 8.1: данные не старше 5 секунд
STALE_AFTER_SECONDS = 5
# ТЗ 8.6: stale, если биржа не отвечала > 30 сек
UNAVAILABLE_AFTER_SECONDS = 30


@dataclass(slots=True)
class Ticker:
    """Последняя цена с биржи по конкретной торговой паре."""
    exchange: str
    pair: str
    bid: float
    ask: float
    last: float | None
    updated_at: datetime

    def age_seconds(self, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        return (now - self.updated_at).total_seconds()

    def stale_level(self, now: datetime | None = None) -> StaleLevel:
        age = self.age_seconds(now)
        if age >= UNAVAILABLE_AFTER_SECONDS:
            return "unavailable"
        if age >= STALE_AFTER_SECONDS:
            return "stale"
        return "ok"


@dataclass
class PriceStore:
    """
    Потокобезопасное хранилище тикеров.
    Ключ — (exchange, pair), значение — Ticker.
    """
    _data: dict[tuple[str, str], Ticker] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def update(self, ticker: Ticker) -> None:
        with self._lock:
            self._data[(ticker.exchange, ticker.pair)] = ticker

    def get(self, exchange: str, pair: str) -> Ticker | None:
        with self._lock:
            return self._data.get((exchange, pair))

    def get_all_for_exchange(self, exchange: str) -> dict[str, Ticker]:
        with self._lock:
            return {
                pair: ticker
                for (ex, pair), ticker in self._data.items()
                if ex == exchange
            }

    def get_all(self) -> dict[tuple[str, str], Ticker]:
        with self._lock:
            return dict(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


# Глобальный singleton — используется всеми коллекторами и API
price_store = PriceStore()


# Список пар MVP — по ТЗ 7.1 (10 пар, топ по объёму USDT).
# На старте зафиксируем 10 популярных; в будущем — динамически.
MVP_PAIRS: list[str] = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    "AVAX/USDT",
    "LINK/USDT",
     
]


def pair_to_stream_symbol(pair: str) -> str:
    """BTC/USDT -> btcusdt (формат Binance stream)."""
    return pair.replace("/", "").lower()


def pair_from_stream_symbol(symbol: str) -> str:
    """btcusdt -> BTC/USDT (для Binance)."""
    symbol = symbol.upper()
    # USDT — самый частый котируемый актив в MVP
    if symbol.endswith("USDT"):
        return f"{symbol[:-4]}/USDT"
    return symbol