from datetime import datetime

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class ExchangeFee(Base, TimestampMixin):
    """
    История taker-комиссий по биржам.
    См. ТЗ раздел 10.5.

    Комиссии версионируются по effective_from / effective_to.
    fee_version в агрегатах и пиках вычисляется из активных версий.
    """
    __tablename__ = "exchange_fees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    exchange: Mapped[str] = mapped_column(String(32), nullable=False)

    # Доля: 0.001 = 0.1%. Numeric(10,6) даёт точность до 0.0001%.
    taker_fee: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)

    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")

    __table_args__ = (
        Index("ix_exchange_fees_exchange_from", "exchange", "effective_from"),
        Index("ix_exchange_fees_effective_range", "exchange", "effective_from", "effective_to"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExchangeFee {self.exchange} {self.taker_fee} "
            f"from={self.effective_from} to={self.effective_to}>"
        )