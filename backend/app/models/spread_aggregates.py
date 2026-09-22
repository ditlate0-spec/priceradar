"""
Минутные агрегаты спредов.
См. ТЗ 8.5 и 10.2.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class SpreadAggregate(Base, TimestampMixin):
    """
    Один минутный агрегат по ряду (pair|exchange_pair|direction).

    Все значения — по spread_net, кроме spread_gross_last (для справки).
    Счётчики seconds_above_* считаются по |spread_net|.
    """
    __tablename__ = "spread_aggregates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    row_id: Mapped[str] = mapped_column(String(128), nullable=False)
    minute_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

        # Net-метрики (основные)
    spread_min: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    spread_max: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    spread_avg_abs: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    spread_avg_signed: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    spread_last: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)

    # Gross-метрики (для переключателя net/gross в v1.1)
    spread_gross_min: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    spread_gross_max: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    spread_gross_avg_abs: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    spread_gross_last: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)

    seconds_above_03: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seconds_above_05: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seconds_above_10: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seconds_above_20: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    stale_level: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")

    threshold_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fee_version: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("row_id", "minute_ts", name="uq_aggregate_row_minute"),
        Index("ix_aggregates_row_minute", "row_id", "minute_ts"),
        Index("ix_aggregates_minute", "minute_ts"),
        Index("ix_aggregates_threshold_minute", "threshold_version", "minute_ts"),
        Index("ix_aggregates_fee_minute", "fee_version", "minute_ts"),
    )

    def __repr__(self) -> str:
        return (
            f"<SpreadAggregate {self.row_id} @ {self.minute_ts} "
            f"min={self.spread_min} max={self.spread_max} n={self.sample_count}>"
        )