"""
Базовый интерфейс коллектора цен.
"""
from abc import ABC, abstractmethod

from loguru import logger

from app.core.store import PriceStore, Ticker


class BaseCollector(ABC):
    """
    Абстрактный коллектор. Наследники реализуют _run_forever().
    Обязанности:
    - подключаться к бирже (WS или REST)
    - парсить сообщения и вызывать self._publish(ticker)
    - корректно завершаться по self._stop_event
    """

    exchange: str = "unknown"

    def __init__(self, store: PriceStore, pairs: list[str]) -> None:
        self.store = store
        self.pairs = pairs
        self._running = False

    @abstractmethod
    async def _run_forever(self) -> None:
        """Основной цикл коллектора. Должен сам обрабатывать reconnect."""
        raise NotImplementedError

    async def start(self) -> None:
        """Запустить коллектор (не блокирует — предполагается create_task)."""
        self._running = True
        logger.info(f"[{self.exchange}] collector starting, pairs={self.pairs}")
        try:
            await self._run_forever()
        except Exception as e:
            logger.exception(f"[{self.exchange}] collector crashed: {e}")
        finally:
            self._running = False
            logger.info(f"[{self.exchange}] collector stopped")

    def stop(self) -> None:
        self._running = False

    def _publish(self, ticker: Ticker) -> None:
        """Сохранить тикер в store."""
        self.store.update(ticker)
        logger.debug(
            f"[{self.exchange}] {ticker.pair} "
            f"bid={ticker.bid} ask={ticker.ask} last={ticker.last}"
        )