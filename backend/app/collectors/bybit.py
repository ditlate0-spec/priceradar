"""
Коллектор Bybit через WebSocket V5 (spot).

Подписка: {"op":"subscribe","args":["orderbook.1.BTCUSDT", ...]}
Сообщение:
{
  "topic": "orderbook.1.BTCUSDT",
  "type": "snapshot",
  "ts": 1234567890,
  "data": {
    "s": "BTCUSDT",
    "b": [["85900.00","1.5"]],   # best bid
    "a": [["85900.10","2.0"]]    # best ask
  }
}
"""
import asyncio
import json
from datetime import datetime, timezone

import websockets
from loguru import logger

from app.collectors.base import BaseCollector
from app.core.store import (
    PriceStore,
    Ticker,
    pair_from_stream_symbol,
    pair_to_stream_symbol,
)

BYBIT_WS_URL = "wss://stream.bybit.com/v5/public/spot"
RECONNECT_DELAY_SECONDS = 5
SUBSCRIBE_CHUNK = 10  # Bybit позволяет до 10 аргументов за раз


class BybitCollector(BaseCollector):
    exchange = "bybit"

    def __init__(self, store: PriceStore, pairs: list[str]) -> None:
        super().__init__(store, pairs)
        self._args = [
            f"orderbook.1.{pair_to_stream_symbol(p).upper()}" for p in self.pairs
        ]

    async def _run_forever(self) -> None:
        while self._running:
            try:
                logger.info(f"[{self.exchange}] connecting to {BYBIT_WS_URL}")
                async with websockets.connect(
                    BYBIT_WS_URL,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as ws:
                    logger.info(f"[{self.exchange}] connected")

                    # Подписка по частям
                    for i in range(0, len(self._args), SUBSCRIBE_CHUNK):
                        chunk = self._args[i:i + SUBSCRIBE_CHUNK]
                        await ws.send(
                            json.dumps({"op": "subscribe", "args": chunk})
                        )
                        logger.info(f"[{self.exchange}] subscribed: {chunk}")

                    async for raw in ws:
                        if not self._running:
                            break
                        await self._handle_message(raw)
            except asyncio.CancelledError:
                logger.info(f"[{self.exchange}] cancelled")
                raise
            except Exception as e:
                logger.warning(
                    f"[{self.exchange}] connection error: {e}. "
                    f"Reconnecting in {RECONNECT_DELAY_SECONDS}s"
                )
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)

    async def _handle_message(self, raw: str | bytes) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        # служебные ответы на subscribe / pong
        if msg.get("op") == "subscribe" or msg.get("success") is not None:
            return

        topic = msg.get("topic", "")
        if not topic.startswith("orderbook."):
            return

        data = msg.get("data") or {}
        symbol = data.get("s")
        if not symbol:
            return

        bids = data.get("b") or []
        asks = data.get("a") or []
        if not bids or not asks:
            return

        try:
            bid = float(bids[0][0])
            ask = float(asks[0][0])
        except (IndexError, ValueError, TypeError):
            return

        pair = pair_from_stream_symbol(symbol)
        ticker = Ticker(
            exchange=self.exchange,
            pair=pair,
            bid=bid,
            ask=ask,
            last=None,
            updated_at=datetime.now(timezone.utc),
        )
        self._publish(ticker)