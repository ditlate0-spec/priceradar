"""
Коллектор OKX через WebSocket V5 (public).

Подписка: {"op":"subscribe","args":[{"channel":"bbo-tbt","instId":"BTC-USDT"}, ...]}
Сообщение:
{
  "arg": {"channel": "bbo-tbt", "instId": "BTC-USDT"},
  "data": [
    {
      "bids": [["85796.4", "0.41", "0", "10"]],
      "asks": [["85796.5", "0.03", "0", "10"]],
      "ts": "1790079539100",
      "seqId": 81456559103
    }
  ]
}
"""
import asyncio
import json
from datetime import datetime, timezone

import websockets
from loguru import logger

from app.collectors.base import BaseCollector
from app.core.store import PriceStore, Ticker

OKX_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
RECONNECT_DELAY_SECONDS = 5
PING_INTERVAL_SECONDS = 20


def _pair_to_okx_instid(pair: str) -> str:
    """BTC/USDT -> BTC-USDT."""
    return pair.replace("/", "-")


def _instid_to_pair(inst_id: str) -> str:
    """BTC-USDT -> BTC/USDT."""
    return inst_id.replace("-", "/")


class OkxCollector(BaseCollector):
    exchange = "okx"

    def __init__(self, store: PriceStore, pairs: list[str]) -> None:
        super().__init__(store, pairs)
        self._args = [
            {"channel": "bbo-tbt", "instId": _pair_to_okx_instid(p)}
            for p in self.pairs
        ]

    async def _run_forever(self) -> None:
        while self._running:
            try:
                logger.info(f"[{self.exchange}] connecting to {OKX_WS_URL}")
                async with websockets.connect(
                    OKX_WS_URL,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=5,
                ) as ws:
                    logger.info(f"[{self.exchange}] connected")

                    await ws.send(
                        json.dumps({"op": "subscribe", "args": self._args})
                    )
                    logger.info(
                        f"[{self.exchange}] subscribed to {len(self._args)} channels"
                    )

                    ping_task = asyncio.create_task(self._ping_loop(ws))

                    try:
                        async for raw in ws:
                            if not self._running:
                                break
                            await self._handle_message(raw)
                    finally:
                        ping_task.cancel()

            except asyncio.CancelledError:
                logger.info(f"[{self.exchange}] cancelled")
                raise
            except Exception as e:
                logger.warning(
                    f"[{self.exchange}] connection error: {e}. "
                    f"Reconnecting in {RECONNECT_DELAY_SECONDS}s"
                )
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)

    async def _ping_loop(self, ws) -> None:
        """OKX требует, чтобы клиент сам отправлял ping каждые <30 сек."""
        try:
            while True:
                await asyncio.sleep(PING_INTERVAL_SECONDS)
                await ws.send("ping")
        except asyncio.CancelledError:
            return
        except Exception:
            return

    async def _handle_message(self, raw: str | bytes) -> None:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")

        if raw == "pong":
            return

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        event = msg.get("event")
        if event == "error":
            logger.warning(f"[{self.exchange}] error event: {msg}")
            return
        if event in {"subscribe", "unsubscribe"}:
            logger.debug(f"[{self.exchange}] {event} ack: {msg.get('arg')}")
            return

        arg = msg.get("arg") or {}
        if arg.get("channel") != "bbo-tbt":
            return

        for item in msg.get("data") or []:
            inst_id = arg.get("instId") or item.get("instId")
            if not inst_id:
                continue

            bids = item.get("bids") or []
            asks = item.get("asks") or []
            if not bids or not asks:
                continue

            try:
                bid = float(bids[0][0])
                ask = float(asks[0][0])
            except (IndexError, ValueError, TypeError):
                continue

            pair = _instid_to_pair(inst_id)
            ticker = Ticker(
                exchange=self.exchange,
                pair=pair,
                bid=bid,
                ask=ask,
                last=None,
                updated_at=datetime.now(timezone.utc),
            )
            self._publish(ticker)