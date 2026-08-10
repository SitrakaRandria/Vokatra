"""
Schémas Pydantic pour le modèle Offer (négociation).
"""
from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict

class OfferBase(BaseModel):
    """Schéma de base pour une offre."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    
    quantity: Decimal = Field(..., gt=0, description="Quantité demandée")
    proposed_price: Decimal = Field(..., gt=0, description="Prix proposé")
    buyer_message: Optional[str] = Field(None, max_length=500)

class OfferCreate(OfferBase):
    """Schéma pour créer une offre."""
    listing_id: int = Field(..., gt=0)

class CounterOfferCreate(BaseModel):
    """Schéma pour une contre-offre."""
    model_config = ConfigDict(extra="forbid")
    
    counter_offer_price: Decimal = Field(..., gt=0)
    counter_offer_quantity: Decimal = Field(..., gt=0)
    seller_response: Optional[str] = Field(None, max_length=500)

class OfferResponse(OfferBase):
    """Schéma de réponse pour une offre."""
    id: int
    listing_id: int
    buyer_id: int
    status: str = "pending"
    counter_offer_price: Optional[Decimal] = None
    counter_offer_quantity: Optional[Decimal] = None
    seller_response: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    
    # Relations optionnelles
    listing: Optional['ListingResponse'] = None
    buyer: Optional['UserResponse'] = None

# Import différé
from app.schemas.listing import ListingResponse
from app.schemas.user import UserResponse
OfferResponse.model_rebuild()
