"""
Менеджер коллекторов: запускает и останавливает всех сборщиков.
"""
import asyncio

from loguru import logger

from app.collectors.base import BaseCollector
from app.collectors.binance import BinanceCollector
from app.collectors.bybit import BybitCollector
from app.collectors.okx import OkxCollector
from app.core.store import MVP_PAIRS, price_store


class CollectorManager:
    def __init__(self) -> None:
        self.collectors: list[BaseCollector] = []
        self.tasks: list[asyncio.Task] = []

    def _build_collectors(self) -> None:
        self.collectors = [
            BinanceCollector(store=price_store, pairs=MVP_PAIRS),
            BybitCollector(store=price_store, pairs=MVP_PAIRS),
            OkxCollector(store=price_store, pairs=MVP_PAIRS),
        ]

    async def start(self) -> None:
        self._build_collectors()
        for collector in self.collectors:
            task = asyncio.create_task(
                collector.start(),
                name=f"collector-{collector.exchange}",
            )
            self.tasks.append(task)
        logger.info(f"Started {len(self.tasks)} collectors")

    async def stop(self) -> None:
        for collector in self.collectors:
            collector.stop()
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        logger.info("All collectors stopped")


collector_manager = CollectorManager()