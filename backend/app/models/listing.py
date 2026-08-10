"""
Modèle Listing pour les annonces de produits agricoles.
"""
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String, Integer, DateTime, Boolean, Numeric, Text, JSON,
    Index, CheckConstraint, Enum, event, and_, or_
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base
from app.utils.validators import validate_positive_decimal

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.offer import Offer
    from app.models.order import Order

class Listing(Base):
    """Modèle d'annonce de vente de produits agricoles."""
    
    __tablename__ = "listings"
    __table_args__ = (
        # Index composites pour les recherches fréquentes
        Index("idx_listing_user_status", "user_id", "status"),
        Index("idx_listing_region_product", "region", "product"),
        Index("idx_listing_date_status", "availability_date", "status"),
        Index("idx_listing_price_quantity", "price", "total_quantity"),
        Index("idx_listing_seasonality", "is_in_season", "product"),
        Index("idx_listing_geo", "region"),  # Pour PostGIS futur
        CheckConstraint("total_quantity > 0", name="ck_listing_positive_quantity"),
        CheckConstraint("available_quantity BETWEEN 0 AND total_quantity", name="ck_listing_available_range"),
        CheckConstraint("price >= 0", name="ck_listing_non_negative_price"),
    )
    
    # Champs primaires
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Référence à l'utilisateur
    user_id: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        index=True,
        doc="ID du vendeur"
    )
    
    # Informations produit
    product: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Quantités
    total_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), 
        nullable=False,
        doc="Quantité totale initiale"
    )
    available_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), 
        nullable=False,
        doc="Quantité encore disponible"
    )
    unit: Mapped[str] = mapped_column(
        Enum('tonne', 'kg', 'litre', 'unité', 'botte', name='unit_types'),
        nullable=False
    )
    
    # Prix
    price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), 
        nullable=False,
        doc="Prix unitaire"
    )
    price_mode: Mapped[str] = mapped_column(
        Enum('with_delivery', 'without_delivery', name='price_modes'),
        nullable=False,
        default='without_delivery'
    )
    
    # Photos
    photos: Mapped[Optional[List[str]]] = mapped_column(
        JSON, 
        nullable=True,
        default=list,
        doc="URLs des photos Cloudinary"
    )
    
    # Localisation
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location_detail: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Saisonnalité
    is_in_season: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False,
        index=True,
        doc="Badge de saisonnalité automatique"
    )
    season_start_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    season_end_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Disponibilité
    availability_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        default=datetime.utcnow
    )
    
    # Statut
    status: Mapped[str] = mapped_column(
        Enum('available', 'partially_sold', 'reserved', 'sold', name='listing_statuses'),
        nullable=False,
        default='available',
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="listings",
        lazy="selectin"  # Évite N+1
    )
    
    offers: Mapped[List["Offer"]] = relationship(
        "Offer",
        back_populates="listing",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="listing",
        cascade="all, delete-orphan"
    )
    
    # Validations
    @validates('total_quantity', 'available_quantity', 'price')
    def validate_positive_numbers(self, key: str, value: Decimal) -> Decimal:
        """Valide que les quantités et prix sont positifs."""
        if not validate_positive_decimal(value):
            raise ValueError(f"{key} doit être positif: {value}")
        return value
    
    @validates('available_quantity')
    def validate_available_quantity(self, key: str, value: Decimal) -> Decimal:
        """Valide que la quantité disponible ne dépasse pas la quantité totale."""
        if hasattr(self, 'total_quantity') and value > self.total_quantity:
            raise ValueError(f"La quantité disponible ({value}) ne peut pas dépasser la quantité totale ({self.total_quantity})")
        return value
    
    # Propriétés hybrides
    @hybrid_property
    def is_fully_sold(self) -> bool:
        """Vérifie si l'annonce est complètement vendue."""
        return self.available_quantity == Decimal('0') or self.status == 'sold'
    
    @hybrid_property
    def remaining_percentage(self) -> float:
        """Calcule le pourcentage restant."""
        if self.total_quantity == Decimal('0'):
            return 0.0
        return float((self.available_quantity / self.total_quantity) * 100)
    
    # Méthodes métier
    def update_availability(self, sold_quantity: Decimal) -> None:
        """
        Met à jour la disponibilité après une vente.
        
        Args:
            sold_quantity: Quantité vendue
            
        Raises:
            ValueError: Si la quantité vendue est invalide
        """
        if sold_quantity <= Decimal('0'):
            raise ValueError(f"Quantité vendue invalide: {sold_quantity}")
        
        if sold_quantity > self.available_quantity:
            raise ValueError(f"Quantité vendue ({sold_quantity}) dépasse la disponibilité ({self.available_quantity})")
        
        # Mise à jour de la quantité disponible
        self.available_quantity -= sold_quantity
        
        # Mise à jour du statut
        if self.available_quantity == Decimal('0'):
            self.status = 'sold'
        elif self.available_quantity < self.total_quantity:
            self.status = 'partially_sold'
        # Si available_quantity == total_quantity, reste 'available'
    
    def reserve(self) -> None:
        """Réserve l'annonce (statut réservé)."""
        if self.status not in ['available', 'partially_sold']:
            raise ValueError(f"Impossible de réserver une annonce en statut {self.status}")
        self.status = 'reserved'
    
    def release_reservation(self) -> None:
        """Libère la réservation."""
        if self.status != 'reserved':
            raise ValueError("Seule une annonce réservée peut être libérée")
        
        # Retour au statut précédent basé sur la disponibilité
        if self.available_quantity == Decimal('0'):
            self.status = 'sold'
        elif self.available_quantity < self.total_quantity:
            self.status = 'partially_sold'
        else:
            self.status = 'available'

# Event listener pour validation automatique
@event.listens_for(Listing, 'before_insert')
@event.listens_for(Listing, 'before_update')
def validate_listing(mapper, connection, target: Listing) -> None:
    """Validation automatique avant insertion/mise à jour."""
    # Vérification cohérence statut/disponibilité
    if target.status == 'sold' and target.available_quantity != Decimal('0'):
        target.available_quantity = Decimal('0')
    
    if target.status == 'available' and target.available_quantity == Decimal('0'):
        raise ValueError("Une annonce disponible doit avoir une quantité disponible > 0")
