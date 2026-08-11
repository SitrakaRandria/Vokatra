"""
Modèle Seasonality pour la table des saisons de produits par région.
"""
from datetime import datetime

from sqlalchemy import (
    Integer, String, DateTime, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.utils.time import utcnow


class Seasonality(Base):
    """Période de saison d'un produit dans une région."""

    __tablename__ = "seasonality"
    __table_args__ = (
        UniqueConstraint("product", "region", name="uq_seasonality_product_region"),
        Index("idx_seasonality_product", "product"),
        Index("idx_seasonality_region", "region"),
        CheckConstraint("month_start BETWEEN 1 AND 12", name="ck_seasonality_month_start"),
        CheckConstraint("month_end BETWEEN 1 AND 12", name="ck_seasonality_month_end"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    product: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)

    # Mois de début/fin de saison (1-12). Une saison peut chevaucher
    # deux années (ex: novembre -> février), month_start > month_end.
    month_start: Mapped[int] = mapped_column(Integer, nullable=False)
    month_end: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    @property
    def months(self) -> list[int]:
        """
        Liste des mois couverts par la saison (gère le chevauchement d'année).

        Returns:
            list[int]: Mois de la saison (ex: [11, 12, 1, 2])
        """
        if self.month_start <= self.month_end:
            return list(range(self.month_start, self.month_end + 1))
        return list(range(self.month_start, 13)) + list(range(1, self.month_end + 1))
