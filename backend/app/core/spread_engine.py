"""
Расчёт спредов между биржами.

См. ТЗ 8.3:
- 9 пар × 3 пары бирж × 2 направления = 54 ряда
- для каждого ряда два значения: spread_gross и spread_net
- итого 108 значений

Формулы:
    spread_gross(A→B) = (bid_A − ask_B) / ask_B × 100%
    spread_net(A→B)   = spread_gross(A→B) − fee_A − fee_B
"""
from dataclasses import dataclass
from itertools import combinations

from app.core.config import get_settings
from app.core.store import PriceStore, Ticker


# Пары бирж (для MVP — 3 пары, но код работает с любым количеством)
EXCHANGE_PAIRS: list[tuple[str, str]] = [
    ("binance", "bybit"),
    ("binance", "okx"),
    ("bybit", "okx"),
]


@dataclass(slots=True)
class SpreadRow:
    """
    Результат расчёта спреда для одного направления одной пары бирж.
    """
    pair: str
    exchange_a: str
    exchange_b: str
    direction: str           # "A→B" или "B→A"
    bid_a: float
    ask_b: float
    spread_gross: float      # в процентах
    spread_net: float        # в процентах
    fee_a: float
    fee_b: float
    stale_a: str             # ok / stale / unavailable
    stale_b: str

    @property
    def row_id(self) -> str:
        """
        Канонический row_id: {pair}|{canonical_exchange_pair}|{direction}.
        canonical_exchange_pair — пара бирж в порядке из EXCHANGE_PAIRS
        (binance-bybit, binance-okx, bybit-okx) — независимо от направления.
        """
        # Канонический порядок: сортируем пару по фиксированному ранжированию
        order = {"binance": 0, "bybit": 1, "okx": 2}
        a, b = self.exchange_a, self.exchange_b
        if order.get(a, 99) > order.get(b, 99):
            a, b = b, a
        return f"{self.pair}|{a}-{b}|{self.direction}"

def _fees() -> dict[str, float]:
    s = get_settings()
    return {
        "binance": s.fee_binance,
        "bybit": s.fee_bybit,
        "okx": s.fee_okx,
    }


def _spread_gross(bid_a: float, ask_b: float) -> float:
    if ask_b <= 0:
        return 0.0
    return (bid_a - ask_b) / ask_b * 100.0


def compute_spread(
    pair: str,
    exchange_a: str,
    exchange_b: str,
    ticker_a: Ticker,
    ticker_b: Ticker,
    fee_a: float,
    fee_b: float,
) -> tuple[SpreadRow, SpreadRow]:
    """
    Считает два направления для пары бирж (A, B):
    A→B и B→A. Это два независимых ряда.
    """
    # A→B: покупаем на B (ask_B), продаём на A (bid_A)
    sg_ab = _spread_gross(ticker_a.bid, ticker_b.ask)
    sn_ab = sg_ab - (fee_a + fee_b) * 100.0  # fee в долях → в %

    # B→A: покупаем на A (ask_A), продаём на B (bid_B)
    sg_ba = _spread_gross(ticker_b.bid, ticker_a.ask)
    sn_ba = sg_ba - (fee_a + fee_b) * 100.0

    stale_a = ticker_a.stale_level()
    stale_b = ticker_b.stale_level()

    row_ab = SpreadRow(
        pair=pair,
        exchange_a=exchange_a,
        exchange_b=exchange_b,
        direction=f"{exchange_a}→{exchange_b}",
        bid_a=ticker_a.bid,
        ask_b=ticker_b.ask,
        spread_gross=round(sg_ab, 6),
        spread_net=round(sn_ab, 6),
        fee_a=fee_a,
        fee_b=fee_b,
        stale_a=stale_a,
        stale_b=stale_b,
    )

    row_ba = SpreadRow(
        pair=pair,
        exchange_a=exchange_b,
        exchange_b=exchange_a,
        direction=f"{exchange_b}→{exchange_a}",
        bid_a=ticker_b.bid,
        ask_b=ticker_a.ask,
        spread_gross=round(sg_ba, 6),
        spread_net=round(sn_ba, 6),
        fee_a=fee_a,
        fee_b=fee_b,
        stale_a=stale_b,
        stale_b=stale_a,
    )

    return row_ab, row_ba


def compute_all_spreads(
    store: PriceStore,
    pairs: list[str],
    exchange_pairs: list[tuple[str, str]] | None = None,
) -> list[SpreadRow]:
    """
    Считает все спреды по всем парам и парам бирж.
    Возвращает список SpreadRow.
    """
    exchange_pairs = exchange_pairs or EXCHANGE_PAIRS
    fees = _fees()
    rows: list[SpreadRow] = []

    for pair in pairs:
        for ex_a, ex_b in exchange_pairs:
            ticker_a = store.get(ex_a, pair)
            ticker_b = store.get(ex_b, pair)

            # Если хотя бы одна биржа не отдала данные — пропускаем ряд
            if ticker_a is None or ticker_b is None:
                continue
            # Если данные старше 30 сек — не считаем (см. ТЗ 8.6)
            if ticker_a.stale_level() == "unavailable":
                continue
            if ticker_b.stale_level() == "unavailable":
                continue

            row_ab, row_ba = compute_spread(
                pair=pair,
                exchange_a=ex_a,
                exchange_b=ex_b,
                ticker_a=ticker_a,
                ticker_b=ticker_b,
                fee_a=fees[ex_a],
                fee_b=fees[ex_b],
            )
            rows.append(row_ab)
            rows.append(row_ba)

    return rows