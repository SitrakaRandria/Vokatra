"""
Modèle Order pour les commandes finalisées (issues d'une annonce ou d'une offre acceptée).
"""
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Integer, Numeric, DateTime, Enum, ForeignKey, CheckConstraint, Index, event
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.utils.validators import validate_positive_decimal

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.listing import Listing
    from app.models.invoice import Invoice

class Order(Base):
    """Commande passée sur une annonce, entre un acheteur et un vendeur."""

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
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.id"), nullable=False, index=True)
    buyer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    seller_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Détails de la commande
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Quantité commandée"
    )
    price_final: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        doc="Prix unitaire final convenu (issu de l'annonce ou d'une offre acceptée)"
    )

    # Statut
    status: Mapped[str] = mapped_column(
        Enum('pending', 'confirmed', 'in_delivery', 'completed', 'cancelled', name='order_statuses'),
        nullable=False,
        default='pending',
        index=True
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

    # Relations
    listing: Mapped["Listing"] = relationship(
        "Listing",
        back_populates="orders",
        lazy="selectin"
    )

    buyer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[buyer_id],
        back_populates="orders_as_buyer",
        lazy="selectin"
    )

    seller: Mapped["User"] = relationship(
        "User",
        foreign_keys=[seller_id],
        back_populates="orders_as_seller",
        lazy="selectin"
    )

    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    # Validations
    @validates('quantity', 'price_final')
    def validate_positive_values(self, key: str, value: Decimal) -> Decimal:
        """Valide que les valeurs numériques sont positives."""
        if value is not None and not validate_positive_decimal(value):
            raise ValueError(f"{key} doit être positif: {value}")
        return value

    # Propriétés hybrides
    @property
    def total_amount(self) -> Decimal:
        """Calcule le montant total de la commande."""
        return self.quantity * self.price_final

    # Méthodes métier
    def confirm(self) -> None:
        """Confirme la commande."""
        if self.status != 'pending':
            raise ValueError(f"Impossible de confirmer une commande en statut {self.status}")
        self.status = 'confirmed'

    def cancel(self) -> None:
        """Annule la commande."""
        if self.status in ('completed', 'cancelled'):
            raise ValueError(f"Impossible d'annuler une commande en statut {self.status}")
        self.status = 'cancelled'

    def complete(self) -> None:
        """Marque la commande comme terminée."""
        if self.status not in ('confirmed', 'in_delivery'):
            raise ValueError(f"Impossible de terminer une commande en statut {self.status}")
        self.status = 'completed'

# Event listener pour la validation automatique
@event.listens_for(Order, 'before_insert')
@event.listens_for(Order, 'before_update')
def validate_order(mapper, connection, target: Order) -> None:
    """Validation automatique avant insertion/mise à jour."""
    if target.buyer_id == target.seller_id:
        raise ValueError("L'acheteur et le vendeur ne peuvent pas être le même utilisateur")
