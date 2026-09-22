"""
Пропущенные минуты — когда агрегат не был записан.
См. ТЗ 8.6 и 10.4.
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class SkippedMinute(Base, TimestampMixin):
    """
    Запись о пропущенной минуте для ряда.
    reason: exchange_down / restart / db_down
    """
    __tablename__ = "skipped_minutes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    row_id: Mapped[str] = mapped_column(String(128), nullable=False)
    minute_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_skipped_row_minute", "row_id", "minute_ts"),
        Index("ix_skipped_minute", "minute_ts"),
    )

    def __repr__(self) -> str:
        return f"<SkippedMinute {self.row_id} @ {self.minute_ts} reason={self.reason}>"