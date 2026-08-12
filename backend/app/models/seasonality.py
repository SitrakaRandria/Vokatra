"""
Modèle Seasonality définissant les périodes de saison par produit et région.
"""
from datetime import datetime

from sqlalchemy import Integer, String, DateTime, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class Seasonality(Base):
    """Définit la période de saison (mois de début/fin) d'un produit dans une région.

    Utilisé par app.core.seasonality.compute_seasonality_badge pour déterminer
    si une annonce doit afficher le badge de saisonnalité.
    """

    __tablename__ = "seasonality"
    __table_args__ = (
        UniqueConstraint("product", "region", name="uq_seasonality_product_region"),
        Index("idx_seasonality_product_region", "product", "region"),
        CheckConstraint("month_start BETWEEN 1 AND 12", name="ck_seasonality_month_start_range"),
        CheckConstraint("month_end BETWEEN 1 AND 12", name="ck_seasonality_month_end_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)

    # Intervalle de mois (1-12). month_start peut être > month_end pour les
    # saisons chevauchant le changement d'année (ex: novembre à février).
    month_start: Mapped[int] = mapped_column(Integer, nullable=False)
    month_end: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
