"""Диагностика: пики в БД."""
import sys
sys.path.insert(0, "/app")

import asyncio

from sqlalchemy import func, select

from app.core.database import get_session_factory
from app.models.peaks import Peak


async def main() -> None:
    factory = get_session_factory()
    async with factory() as s:
        total = (await s.execute(select(func.count()).select_from(Peak))).scalar_one()
        open_peaks = (
            await s.execute(
                select(func.count()).select_from(Peak).where(Peak.time_end.is_(None))
            )
        ).scalar_one()
        print(f"всего пиков: {total}")
        print(f"открытых (time_end NULL): {open_peaks}")
        print()

        rows = (
            await s.execute(
                select(Peak).order_by(Peak.time_start.desc()).limit(20)
            )
        ).scalars().all()

        if not rows:
            print("(список пуст)")
            return

        for p in rows:
            end = p.time_end.isoformat() if p.time_end else "OPEN"
            print(
                f"  id={p.id:>3} {p.row_id:<40} thr={float(p.threshold):.1f} "
                f"start={p.time_start.isoformat()} end={end} "
                f"max={float(p.spread_max_abs):.4f} dur_data={p.duration_data_seconds}"
            )


if __name__ == "__main__":
    asyncio.run(main())