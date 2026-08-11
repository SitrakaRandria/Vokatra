from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Integer, String, Numeric, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User

class TransporterProfile(Base):
    __tablename__ = "transporter_profiles"
    __table_args__ = (
        Index("idx_transporter_region", "coverage_region"),
        Index("idx_transporter_availability", "is_available"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    coverage_region: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    base_rate: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    rate_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="per_km")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="transporter_profile")
