"""
Modèle Offer pour le système de négociation.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Integer, String, DateTime, Numeric, Enum, CheckConstraint, Index, ForeignKey, event
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base
from app.utils.validators import validate_positive_decimal
from app.utils.time import utcnow

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
    listing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("listings.id"), nullable=False, index=True
    )
    buyer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    
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
        default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=utcnow,
        onupdate=utcnow
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
    def validate_positive_values(self, key: str, value: Decimal) -> Decimal:
        """Valide que les valeurs numériques sont positives."""
        if value is not None and not validate_positive_decimal(value):
            raise ValueError(f"{key} doit être positif: {value}")
        # NB: la quantité demandée vs la disponibilité de l'annonce est
        # vérifiée au niveau du service (endpoint), car elle dépend du listing.
        return value
    
    # Propriétés hybrides
    @hybrid_property
    def is_counter_offer(self) -> bool:
        """Vérifie si l'offre est une contre-offre."""
        return self.status == 'counter_offer'
    
    @hybrid_property
    def is_active(self) -> bool:
        """Vérifie si l'offre est toujours active."""
        return self.status in ['pending', 'counter_offer']
    
    # Méthodes métier
    def accept(self) -> None:
        """Accepte l'offre."""
        if self.status not in ['pending', 'counter_offer']:
            raise ValueError(f"Impossible d'accepter une offre en statut {self.status}")
        self.status = 'accepted'
    
    def refuse(self) -> None:
        """Refuse l'offre."""
        if self.status not in ['pending', 'counter_offer']:
            raise ValueError(f"Impossible de refuser une offre en statut {self.status}")
        self.status = 'refused'
    
    def create_counter_offer(self, price: Decimal, quantity: Decimal) -> None:
        """
        Crée une contre-offre.
        
        Args:
            price: Nouveau prix proposé
            quantity: Nouvelle quantité proposée
            
        Raises:
            ValueError: Si les paramètres sont invalides
        """
        if not validate_positive_decimal(price):
            raise ValueError(f"Prix de contre-offre invalide: {price}")
        if not validate_positive_decimal(quantity):
            raise ValueError(f"Quantité de contre-offre invalide: {quantity}")
        
        self.status = 'counter_offer'
        self.counter_offer_price = price
        self.counter_offer_quantity = quantity
        self.updated_at = utcnow()

# Event listener pour expiration automatique
@event.listens_for(Offer, 'before_insert')
@event.listens_for(Offer, 'before_update')
def set_expiration(mapper, connection, target: Offer) -> None:
    """Définit une date d'expiration automatique si non définie."""
    if target.expires_at is None:
        from datetime import timedelta
        target.expires_at = utcnow() + timedelta(days=7)
