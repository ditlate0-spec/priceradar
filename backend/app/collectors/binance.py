"""
Коллектор Binance через WebSocket.

Использует combined stream bookTicker:
wss://stream.binance.com:9443/stream?streams=btcusdt@bookTicker/ethusdt@bookTicker/...

bookTicker отдаёт:
{
  "u": 400900217,      // updateId
  "s": "BNBUSDT",      // symbol
  "b": "25.35190000",  // best bid price
  "B": "31.21000000",  // best bid qty
  "a": "25.36520000",  // best ask price
  "A": "40.66000000"   // best ask qty
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

BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream?streams="
RECONNECT_DELAY_SECONDS = 5


class BinanceCollector(BaseCollector):
    exchange = "binance"

    def __init__(self, store: PriceStore, pairs: list[str]) -> None:
        super().__init__(store, pairs)
        self._url = self._build_url()

    def _build_url(self) -> str:
        streams = "/".join(
            f"{pair_to_stream_symbol(p)}@bookTicker" for p in self.pairs
        )
        return f"{BINANCE_WS_BASE}{streams}"

    async def _run_forever(self) -> None:
        while self._running:
            try:
                logger.info(f"[{self.exchange}] connecting to {self._url}")
                async with websockets.connect(
                    self._url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as ws:
                    logger.info(f"[{self.exchange}] connected")
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
            logger.warning(f"[{self.exchange}] non-JSON message: {raw[:100]}")
            return

        # Combined stream: данные в поле "data"
        data = msg.get("data", msg)
        symbol = data.get("s")
        if not symbol:
            return

        try:
            bid = float(data["b"])
            ask = float(data["a"])
        except (KeyError, ValueError, TypeError):
            return

        pair = pair_from_stream_symbol(symbol)
        ticker = Ticker(
            exchange=self.exchange,
            pair=pair,
            bid=bid,
            ask=ask,
            last=None,  # bookTicker не отдаёт last
            updated_at=datetime.now(timezone.utc),
        )
        self._publish(ticker)