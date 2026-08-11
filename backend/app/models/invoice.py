"""
Modèle Invoice (facture) pour les comptes professionnels vérifiés.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Integer, DateTime, Numeric, Enum, String, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.order import Order


class Invoice(Base):
    """Facture émise pour une commande."""

    __tablename__ = "invoices"
    __table_args__ = (
        Index("idx_invoice_order", "order_id"),
        Index("idx_invoice_issuer", "issuer_id"),
        Index("idx_invoice_recipient", "recipient_id"),
        Index("idx_invoice_status", "status"),
        CheckConstraint("amount >= 0", name="ck_invoice_non_negative_amount"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Références
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False, unique=True, index=True
    )
    issuer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    recipient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    # Montant et statut
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        doc="Montant total de la facture (TTC)"
    )
    status: Mapped[str] = mapped_column(
        Enum('generated', 'paid', 'cancelled', name='invoice_statuses'),
        nullable=False,
        default='generated',
        index=True
    )
    pdf_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="URL de téléchargement du PDF"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relations
    order: Mapped["Order"] = relationship("Order", back_populates="invoice", lazy="selectin")
    issuer: Mapped["User"] = relationship(
        "User", foreign_keys=[issuer_id], back_populates="invoices_issued", lazy="selectin"
    )
    recipient: Mapped["User"] = relationship(
        "User", foreign_keys=[recipient_id], back_populates="invoices_received", lazy="selectin"
    )

    # Méthodes métier
    def mark_paid(self) -> None:
        """Marque la facture comme payée."""
        if self.status == 'cancelled':
            raise ValueError("Une facture annulée ne peut pas être payée")
        self.status = 'paid'
        self.paid_at = utcnow()

    def cancel(self) -> None:
        """Annule la facture."""
        if self.status == 'paid':
            raise ValueError("Une facture payée ne peut pas être annulée")
        self.status = 'cancelled'
