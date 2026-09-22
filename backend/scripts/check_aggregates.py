"""Диагностика: посмотреть агрегаты в БД, сгруппированные по минутам."""
import asyncio
import sys
from pathlib import Path

# /app/scripts/check_aggregates.py -> /app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import func, select

from app.core.database import get_session_factory
from app.models.spread_aggregates import SpreadAggregate


async def main() -> None:
    factory = get_session_factory()
    async with factory() as s:
        rows = (
            await s.execute(
                select(
                    SpreadAggregate.minute_ts,
                    func.count(SpreadAggregate.id).label("n"),
                    func.min(SpreadAggregate.sample_count).label("sc_min"),
                    func.max(SpreadAggregate.sample_count).label("sc_max"),
                    func.avg(SpreadAggregate.spread_avg_abs).label("avg_spread"),
                )
                .group_by(SpreadAggregate.minute_ts)
                .order_by(SpreadAggregate.minute_ts)
            )
        ).all()

        header = f'{"minute_ts":<28} {"n":>4} {"sc_min":>7} {"sc_max":>7} {"avg_abs":>9}'
        print(header)
        print("-" * len(header))
        for r in rows:
            print(
                f"{str(r.minute_ts):<28} {r.n:>4} {r.sc_min:>7} {r.sc_max:>7} "
                f"{float(r.avg_spread):>9.4f}"
            )


if __name__ == "__main__":
    asyncio.run(main())