"""Диагностика: последний агрегат, net и gross метрики."""
import sys
sys.path.insert(0, "/app")

import asyncio

from sqlalchemy import select

from app.core.database import get_session_factory
from app.models.spread_aggregates import SpreadAggregate


async def main() -> None:
    factory = get_session_factory()
    async with factory() as s:
        row = (
            await s.execute(
                select(SpreadAggregate).order_by(SpreadAggregate.id.desc()).limit(1)
            )
        ).scalar_one()
        print("id:", row.id)
        print("minute_ts:", row.minute_ts)
        print("row_id:", row.row_id)
        print()
        print("net:")
        print("  min       =", row.spread_min)
        print("  max       =", row.spread_max)
        print("  avg_abs   =", row.spread_avg_abs)
        print("  avg_signed=", row.spread_avg_signed)
        print("  last      =", row.spread_last)
        print()
        print("gross:")
        print("  min       =", row.spread_gross_min)
        print("  max       =", row.spread_gross_max)
        print("  avg_abs   =", row.spread_gross_avg_abs)
        print("  last      =", row.spread_gross_last)
        print()
        print("sample_count:", row.sample_count)
        print("partial:", row.partial)


if __name__ == "__main__":
    asyncio.run(main())