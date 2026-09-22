"""
Эндпоинты текущих цен и спредов.
"""
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.spread_engine import compute_all_spreads
from app.core.store import MVP_PAIRS, price_store
from app.core.thresholds import get_highlight_level

router = APIRouter(prefix="/api/v1/spreads", tags=["spreads"])


@router.get("/current")
async def current_spreads():
    now = datetime.now(timezone.utc)

    # --- Цены ---
    prices = []
    for (exchange, pair), ticker in price_store.get_all().items():
        prices.append({
            "exchange": exchange,
            "pair": pair,
            "bid": ticker.bid,
            "ask": ticker.ask,
            "last": ticker.last,
            "updated_at": ticker.updated_at.isoformat(),
            "age_seconds": round(ticker.age_seconds(now), 2),
            "stale_level": ticker.stale_level(now),
        })
    prices.sort(key=lambda x: (x["pair"], x["exchange"]))

    # --- Спреды ---
    rows = compute_all_spreads(price_store, MVP_PAIRS)
    spreads = []
    for row in rows:
        level = get_highlight_level(row.spread_net)
        spreads.append({
            "row_id": row.row_id,
            "pair": row.pair,
            "exchange_a": row.exchange_a,
            "exchange_b": row.exchange_b,
            "direction": row.direction,
            "bid_a": row.bid_a,
            "ask_b": row.ask_b,
            "spread_gross": row.spread_gross,
            "spread_net": row.spread_net,
            "level": level.value,
            "fee_a": row.fee_a,
            "fee_b": row.fee_b,
            "stale_a": row.stale_a,
            "stale_b": row.stale_b,
        })

    spreads.sort(key=lambda x: -abs(x["spread_net"]))

    return {
        "as_of": now.isoformat(),
        "prices_count": len(prices),
        "spreads_count": len(spreads),
        "prices": prices,
        "spreads": spreads,
    }