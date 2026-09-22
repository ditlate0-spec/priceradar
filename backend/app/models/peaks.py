"""
Пики — отклонения spread_net выше порогов пиков.
См. ТЗ 10.3.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class Peak(Base, TimestampMixin):
    """
    Пик — превышение |spread_net| над порогом пика.

    Открывается при первом превышении, закрывается после 3 секунд ниже порога.
    При пропусках данных пик переходит в состояние «пауза» (is_paused=True).
    """
    __tablename__ = "peaks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    row_id: Mapped[str] = mapped_column(String(128), nullable=False)
    threshold: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)

    threshold_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fee_version: Mapped[str] = mapped_column(String(64), nullable=False)

    time_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_data_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    spread_max_abs: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    spread_avg_abs: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    time_max: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Накопитель суммы |spread_net| за пик — нужен для avg
    sum_abs: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False, default=0)

    is_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_peaks_row_time_start", "row_id", "time_start"),
        Index("ix_peaks_time_start", "time_start"),
        Index("ix_peaks_threshold_time", "threshold", "time_start"),
        Index("ix_peaks_open", "time_end", "is_paused"),
    )

    def __repr__(self) -> str:
        return (
            f"<Peak {self.row_id} thr={self.threshold} "
            f"start={self.time_start} end={self.time_end}>"
        )