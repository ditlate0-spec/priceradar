"""
Экспорт агрегатов спреда в CSV / JSON.
См. ТЗ 14.7.

GET /api/v1/export
  ?pair=BTC/USDT
  &exchange_pair=binance-okx
  &direction=binance-okx
  &from=...&to=...
  &format=csv|json
  &metric=net|gross|both
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.database import get_session_factory
from app.models.spread_aggregates import SpreadAggregate

router = APIRouter(prefix="/api/v1/export", tags=["export"])


def _direction_dash_to_arrow(direction: str) -> str:
    if "→" in direction:
        return direction
    parts = direction.split("-")
    if len(parts) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"direction должен быть в формате 'exchange_a-exchange_b', получено: {direction!r}",
        )
    return f"{parts[0]}→{parts[1]}"


def _build_row_id(pair: str, exchange_pair: str, direction: str) -> str:
    arrow = _direction_dash_to_arrow(direction)
    return f"{pair}|{exchange_pair}|{arrow}"


# Колонки CSV. Английские — чтобы Excel / pandas не ломались.
CSV_COLUMNS = [
    "minute_ts",
    "row_id",
    "spread_min",
    "spread_max",
    "spread_avg_abs",
    "spread_avg_signed",
    "spread_last",
    "spread_gross_min",
    "spread_gross_max",
    "spread_gross_avg_abs",
    "spread_gross_last",
    "seconds_above_03",
    "seconds_above_05",
    "seconds_above_10",
    "seconds_above_20",
    "sample_count",
    "partial",
    "stale_level",
    "threshold_version",
    "fee_version",
]


@router.get("")
async def export_aggregates(
    pair: str = Query(..., description="BTC/USDT"),
    exchange_pair: str = Query(..., description="binance-okx"),
    direction: str = Query(..., description="binance-okx"),
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
    format: str = Query("csv", description="csv | json"),
    metric: str = Query("both", description="net | gross | both"),
):
    if format not in ("csv", "json"):
        raise HTTPException(status_code=400, detail="format должен быть 'csv' или 'json'")
    if metric not in ("net", "gross", "both"):
        raise HTTPException(status_code=400, detail="metric должен быть 'net', 'gross' или 'both'")

    row_id = _build_row_id(pair, exchange_pair, direction)

    if to_ts is None:
        to_ts = datetime.now(timezone.utc)
    if from_ts is None:
        from_ts = to_ts - timedelta(hours=24)

    if (to_ts - from_ts).days > 90:
        raise HTTPException(
            status_code=400,
            detail="Максимальный диапазон from/to — 90 дней",
        )

    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                select(SpreadAggregate)
                .where(
                    SpreadAggregate.row_id == row_id,
                    SpreadAggregate.minute_ts >= from_ts,
                    SpreadAggregate.minute_ts <= to_ts,
                )
                .order_by(SpreadAggregate.minute_ts)
            )
        ).scalars().all()

    # Имя файла
    filename_base = (
        f"priceradar_{pair.replace('/', '')}_{exchange_pair}_{direction}_"
        f"{from_ts.strftime('%Y%m%d')}_{to_ts.strftime('%Y%m%d')}"
    )

    if format == "json":
        data = {
            "row_id": row_id,
            "from": from_ts.isoformat(),
            "to": to_ts.isoformat(),
            "metric": metric,
            "count": len(rows),
            "points": [_row_to_dict(r) for r in rows],
        }
        body = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(body),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.json"',
            },
        )

    # CSV
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for r in rows:
        writer.writerow(_row_to_list(r, metric))

    # BOM — чтобы Excel корректно открыл UTF-8
    body = ("\ufeff" + buf.getvalue()).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(body),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename_base}.csv"',
        },
    )


def _row_to_dict(r: SpreadAggregate) -> dict:
    return {col: _cell_value(r, col) for col in CSV_COLUMNS}


def _row_to_list(r: SpreadAggregate, metric: str) -> list:
    row = []
    for col in CSV_COLUMNS:
        if metric == "net" and col.startswith("spread_gross"):
            continue
        if metric == "gross" and col.startswith("spread_") and not col.startswith("spread_gross"):
            continue
        row.append(_cell_value(r, col))
    return row


def _cell_value(r: SpreadAggregate, col: str):
    v = getattr(r, col, None)
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.isoformat()
    if hasattr(v, "__float__"):
        # Decimal → float
        try:
            return float(v)
        except (TypeError, ValueError):
            return str(v)
    return v