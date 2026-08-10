"""
Modèle Offer pour le système de négociation.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Integer, DateTime, Numeric, Enum, CheckConstraint, Index, event
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.utils.validators import validate_positive_decimal

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.listing import Listing

class Offer(Base):
    """Modèle d'offre/contre-offre pour une annonce."""
    
    __tablename__ = "offers"
    __table_args__ = (
        Index("idx_offer_listing_buyer", "listing_id", "buyer_id"),
        Index("idx_offer_status_date", "status", "created_at"),
        CheckConstraint("quantity > 0", name="ck_offer_positive_quantity"),
        CheckConstraint("proposed_price >= 0", name="ck_offer_non_negative_price"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Références
    listing_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    buyer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Détails de l'offre
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), 
        nullable=False,
        doc="Quantité demandée"
    )
    proposed_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), 
        nullable=False,
        doc="Prix proposé par l'acheteur"
    )
    
    # Statut de l'offre
    status: Mapped[str] = mapped_column(
        Enum('pending', 'accepted', 'refused', 'counter_offer', name='offer_statuses'),
        nullable=False,
        default='pending',
        index=True
    )
    
    # Contre-offre
    counter_offer_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), 
        nullable=True,
        doc="Prix de la contre-offre (si applicable)"
    )
    counter_offer_quantity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), 
        nullable=True,
        doc="Quantité de la contre-offre (si applicable)"
    )
    
    # Messages associés
    buyer_message: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True,
        doc="Message de l'acheteur"
    )
    seller_response: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True,
        doc="Réponse du vendeur"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        doc="Date d'expiration de l'offre (défaut: 7 jours)"
    )
    
    # Relations
    listing: Mapped["Listing"] = relationship(
        "Listing",
        back_populates="offers",
        lazy="selectin"
    )
    
    buyer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[buyer_id],
        back_populates="offers_made",
        lazy="selectin"
    )
    
    # Validations
    @validates('quantity', 'proposed_price', 'counter_offer_price', 'counter_offer_quantity')
    def validate_positive_values(self, key: str, value: Decimal
