"""
Modèle User avec validation métier et index optimisés.
"""
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String, Integer, Enum, DateTime, Boolean, Numeric, Text, 
    UniqueConstraint, Index, CheckConstraint, event,JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import JSON


from app.core.database import Base
from app.utils.validators import validate_phone_madagascar

if TYPE_CHECKING:
    from app.models.listing import Listing
    from app.models.offer import Offer
    from app.models.order import Order
    from app.models.message import Message
    from app.models.invoice import Invoice
    from app.models.transporter import TransporterProfile

class User(Base):
    """Modèle utilisateur de la plateforme Vokatra."""
    
    __tablename__ = "users"
    __table_args__ = (
        # Index pour les recherches fréquentes
        Index("idx_user_phone", "phone"),
        Index("idx_user_role_region", "role", "region"),
        Index("idx_user_verification_status", "verification_status"),
        UniqueConstraint("phone", name="uq_user_phone"),
        CheckConstraint("rating BETWEEN 0 AND 5", name="ck_user_rating_range"),
    )
    
    # Champs primaires
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Identifiants et contact
    phone: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        unique=True,
        doc="Numéro de téléphone malgache (format: +261XXXXXXXXX)"
    )
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Identité
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum('agriculteur', 'collecteur', 'grossiste', 'transporteur', name='user_roles'),
        nullable=False
    )
    account_type: Mapped[str] = mapped_column(
        Enum('physical', 'professional', name='account_types'),
        nullable=False,
        default='physical'
    )
    
    # Localisation
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Statut de vérification
    verification_status: Mapped[str] = mapped_column(
        Enum('base', 'pending', 'professional', 'verified', name='verification_statuses'),
        nullable=False,
        default='base'
    )
    verification_documents: Mapped[Optional[dict]] = mapped_column(
        JSON,  # Utiliser JSON au lieu de dict
        nullable=True,
        doc="Documents de vérification: CIN_url, NIF, carte_stat_url"
    )

    # Profil et réputation
    profile_picture: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rating: Mapped[float] = mapped_column(
        Numeric(3, 2), 
        nullable=False, 
        default=Decimal('0.00')
    )
    total_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Entreprise (pour comptes professionnels)
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    company_registration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
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
    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Relations
    listings: Mapped[List["Listing"]] = relationship(
        "Listing", 
        back_populates="user", 
        cascade="all, delete-orphan",
        lazy="selectin"  # Évite N+1
    )
    
    offers_made: Mapped[List["Offer"]] = relationship(
        "Offer", 
        foreign_keys="Offer.buyer_id",
        back_populates="buyer",
        cascade="all, delete-orphan"
    )
    
    offers_received: Mapped[List["Offer"]] = relationship(
        "Offer",
        foreign_keys="Offer.listing_id",  # Note: ce n'est pas un foreign key direct à User, mais à Listing
        viewonly=True  # Relation en lecture seule via listing
    )
    
    orders_as_buyer: Mapped[List["Order"]] = relationship(
        "Order",
        foreign_keys="Order.buyer_id",
        back_populates="buyer"
    )
    
    orders_as_seller: Mapped[List["Order"]] = relationship(
        "Order",
        foreign_keys="Order.seller_id",
        back_populates="seller"
    )
    
    sent_messages: Mapped[List["Message"]] = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender"
    )
    
    transporter_profile: Mapped[Optional["TransporterProfile"]] = relationship(
        "TransporterProfile",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    invoices_issued: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        foreign_keys="Invoice.issuer_id",
        back_populates="issuer"
    )
    
    invoices_received: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        foreign_keys="Invoice.recipient_id",
        back_populates="recipient"
    )
    
    # Validations
    @validates('phone')
    def validate_phone(self, key: str, phone: str) -> str:
        """
        Valide le format du numéro de téléphone malgache.
        
        Args:
            key: Nom du champ
            phone: Numéro à valider
            
        Returns:
            str: Numéro validé
            
        Raises:
            ValueError: Si le format est invalide
        """
        if not validate_phone_madagascar(phone):
            raise ValueError(f"Numéro de téléphone invalide: {phone}. Format attendu: +261XXXXXXXXX")
        return phone
    
    @validates('rating')
    def validate_rating(self, key: str, rating: float) -> float:
        """Valide que la note est entre 0 et 5."""
        if rating < 0 or rating > 5:
            raise ValueError(f"La note doit être entre 0 et 5: {rating}")
        return rating
    
    # Propriétés hybrides
    @hybrid_property
    def display_name(self) -> str:
        """Retourne le nom affiché (nom complet ou entreprise)."""
        if self.account_type == 'professional' and self.company_name:
            return f"{self.company_name} ({self.full_name})"
        return self.full_name
    
    @hybrid_property
    def is_verified_professional(self) -> bool:
        """Vérifie si l'utilisateur est un professionnel vérifié."""
        return self.account_type == 'professional' and self.verification_status == 'verified'
    
    # Méthodes métier
    def can_issue_invoices(self) -> bool:
        """
        Détermine si l'utilisateur peut émettre des factures.
        
        Returns:
            bool: True si l'utilisateur a un compte professionnel vérifié
        """
        return self.account_type == 'professional' and self.verification_status == 'verified'
    
    def update_rating(self, new_rating: float) -> None:
        """
        Met à jour la note moyenne de l'utilisateur avec gestion d'erreur.
        
        Args:
            new_rating: Nouvelle note à intégrer
            
        Raises:
            ValueError: Si la note est invalide
        """
        if not (0 <= new_rating <= 5):
            raise ValueError(f"Note invalide: {new_rating}")
        
        # Calcul de la nouvelle moyenne
        current_total = self.rating * self.total_transactions if self.total_transactions > 0 else 0
        self.total_transactions += 1
        # Protection contre division par zéro
        self.rating = (current_total + new_rating) / self.total_transactions

# Event listeners pour la validation automatique
@event.listens_for(User, 'before_insert')
@event.listens_for(User, 'before_update')
def validate_user(mapper, connection, target: User) -> None:
    """Validation automatique avant insertion/mise à jour."""
    if target.rating < 0 or target.rating > 5:
        raise ValueError(f"Rating invalide: {target.rating}")
    
    # Vérification que les documents de vérification sont cohérents
    if target.verification_status == 'verified' and not target.verification_documents:
        raise ValueError("Un utilisateur vérifié doit avoir des documents de vérification")

# Ajouter ce champ
hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
