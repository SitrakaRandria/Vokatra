"""
Modèle Invoice pour les factures émises par les comptes professionnels vérifiés.
"""
from typing import TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Integer, String, Numeric, DateTime, Enum, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.utils.validators import validate_positive_decimal

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.order import Order

class Invoice(Base):
    """Facture générée pour une commande, émise par le vendeur (professionnel vérifié)."""

    __tablename__ = "invoices"
    __table_args__ = (
        Index("idx_invoice_order", "order_id"),
        Index("idx_invoice_issuer", "issuer_id"),
        Index("idx_invoice_recipient", "recipient_id"),
        CheckConstraint("amount >= 0", name="ck_invoice_non_negative_amount"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Références
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    issuer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipient_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Détails de la facture
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        doc="Montant total de la facture"
    )
    status: Mapped[str] = mapped_column(
        Enum('generated', 'sent', 'paid', 'cancelled', name='invoice_statuses'),
        nullable=False,
        default='generated'
    )
    pdf_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="URL/chemin vers le PDF généré de la facture"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    # Relations
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="invoices",
        lazy="selectin"
    )

    issuer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[issuer_id],
        back_populates="invoices_issued",
        lazy="selectin"
    )

    recipient: Mapped["User"] = relationship(
        "User",
        foreign_keys=[recipient_id],
        back_populates="invoices_received",
        lazy="selectin"
    )

    # Validations
    @validates('amount')
    def validate_amount(self, key: str, value: Decimal) -> Decimal:
        """Valide que le montant est positif ou nul."""
        if value is not None and value < 0:
            raise ValueError(f"Le montant de la facture doit être positif ou nul: {value}")
        return value
