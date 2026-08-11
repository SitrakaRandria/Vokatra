from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, String, Numeric, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("product", "region", "month_year", name="uq_price_history_period"),
        Index("idx_price_history_product_region", "product", "region"),
        Index("idx_price_history_month", "month_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    avg_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    min_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    max_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    month_year: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
