"""
Modèle Order (commande) pour le suivi des transactions Vokatra.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Integer, DateTime, Numeric, Enum, ForeignKey, Index, CheckConstraint, event
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.listing import Listing
    from app.models.invoice import Invoice


class Order(Base):
    """Commande créée lors de l'acceptation d'une offre."""

    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_order_listing", "listing_id"),
        Index("idx_order_buyer", "buyer_id"),
        Index("idx_order_seller", "seller_id"),
        Index("idx_order_status_date", "status", "created_at"),
        CheckConstraint("quantity > 0", name="ck_order_positive_quantity"),
        CheckConstraint("price_final >= 0", name="ck_order_non_negative_price"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Références
    listing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("listings.id"), nullable=False, index=True
    )
    buyer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    seller_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    # Détails commerciaux
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Quantité commandée"
    )
    price_final: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        doc="Prix unitaire final négocié"
    )

    # Statut
    status: Mapped[str] = mapped_column(
        Enum('pending', 'confirmed', 'delivered', 'cancelled', name='order_statuses'),
        nullable=False,
        default='pending',
        index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    # Relations
    listing: Mapped["Listing"] = relationship("Listing", back_populates="orders", lazy="selectin")
    buyer: Mapped["User"] = relationship(
        "User", foreign_keys=[buyer_id], back_populates="orders_as_buyer", lazy="selectin"
    )
    seller: Mapped["User"] = relationship(
        "User", foreign_keys=[seller_id], back_populates="orders_as_seller", lazy="selectin"
    )
    invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice", back_populates="order", uselist=False, cascade="all, delete-orphan"
    )

    # Propriétés hybrides
    @property
    def total_amount(self) -> Decimal:
        """Montant total de la commande."""
        return (self.quantity or Decimal('0')) * (self.price_final or Decimal('0'))

    # Méthodes métier
    def confirm(self) -> None:
        """Confirme la commande."""
        if self.status != 'pending':
            raise ValueError(f"Impossible de confirmer une commande en statut {self.status}")
        self.status = 'confirmed'

    def mark_delivered(self) -> None:
        """Marque la commande comme livrée."""
        if self.status not in ('pending', 'confirmed'):
            raise ValueError(f"Impossible de livrer une commande en statut {self.status}")
        self.status = 'delivered'

    def cancel(self) -> None:
        """Annule la commande."""
        if self.status == 'delivered':
            raise ValueError("Une commande livrée ne peut pas être annulée")
        self.status = 'cancelled'


# Event listener pour validation automatique
@event.listens_for(Order, 'before_insert')
@event.listens_for(Order, 'before_update')
def validate_order(mapper, connection, target: Order) -> None:
    """Validation automatique avant insertion/mise à jour."""
    if target.quantity <= Decimal('0'):
        raise ValueError(f"Quantité invalide: {target.quantity}")
    if target.price_final < Decimal('0'):
        raise ValueError(f"Prix final invalide: {target.price_final}")
