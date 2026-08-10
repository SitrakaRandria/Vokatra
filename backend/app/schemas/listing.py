"""
Schémas Pydantic pour le modèle Listing avec validation métier.
"""
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic.types import StringConstraints
from typing_extensions import Annotated

# Type pour les quantités positives
PositiveDecimal = Annotated[
    Decimal,
    Field(gt=0, decimal_places=2)
]

class ListingBase(BaseModel):
    """Schéma de base pour une annonce."""
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True
    )
    
    product: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    total_quantity: PositiveDecimal = Field(..., description="Quantité totale")
    unit: str = Field(..., pattern="^(tonne|kg|litre|unité|botte)$")
    price: PositiveDecimal = Field(..., description="Prix unitaire")
    price_mode: str = Field(default="without_delivery", pattern="^(with_delivery|without_delivery)$")
    region: str = Field(..., min_length=2, max_length=100)
    location_detail: Optional[str] = Field(None, max_length=200)
    availability_date: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('total_quantity')
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= Decimal('0'):
            raise ValueError("La quantité totale doit être positive")
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v < Decimal('0'):
            raise ValueError("Le prix ne peut pas être négatif")
        return v

class ListingCreate(ListingBase):
    """Schéma pour la création d'une annonce."""
    photos: Optional[List[str]] = Field(default_factory=list, max_length=5)
    
    @field_validator('photos')
    @classmethod
    def validate_photos(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if len(v) > 5:
                raise ValueError("Maximum 5 photos autorisées")
            for url in v:
                if not url.startswith(('http://', 'https://')):
                    raise ValueError(f"URL de photo invalide: {url}")
        return v

class ListingUpdate(BaseModel):
    """Schéma pour la mise à jour d'une annonce."""
    model_config = ConfigDict(extra="forbid")
    
    product: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    total_quantity: Optional[PositiveDecimal] = None
    unit: Optional[str] = Field(None, pattern="^(tonne|kg|litre|unité|botte)$")
    price: Optional[PositiveDecimal] = None
    price_mode: Optional[str] = Field(None, pattern="^(with_delivery|without_delivery)$")
    region: Optional[str] = Field(None, min_length=2, max_length=100)
    location_detail: Optional[str] = Field(None, max_length=200)
    availability_date: Optional[datetime] = None
    photos: Optional[List[str]] = Field(None, max_length=5)
    status: Optional[str] = Field(None, pattern="^(available|partially_sold|reserved|sold)$")
    
    @field_validator('photos')
    @classmethod
    def validate_photos(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None and len(v) > 5:
            raise ValueError("Maximum 5 photos autorisées")
        return v

class ListingResponse(ListingBase):
    """Schéma de réponse pour une annonce."""
    id: int
    user_id: int
    available_quantity: Decimal = Field(..., ge=0)
    is_in_season: bool = False
    status: str = "available"
    photos: Optional[List[str]] = Field(default_factory=list)
    season_start_month: Optional[int] = None
    season_end_month: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    # Relations (optionnel)
    user: Optional['UserResponse'] = None
    
    # Propriété calculée
    @field_validator('available_quantity')
    @classmethod
    def validate_available(cls, v: Decimal, info) -> Decimal:
        total = info.data.get('total_quantity', Decimal('0'))
        if v > total:
            raise ValueError("La quantité disponible ne peut pas dépasser la quantité totale")
        return v

class ListingFilterParams(BaseModel):
    """Paramètres de filtrage pour les listings."""
    product: Optional[str] = None
    region: Optional[str] = None
    min_price: Optional[PositiveDecimal] = None
    max_price: Optional[PositiveDecimal] = None
    min_quantity: Optional[PositiveDecimal] = None
    status: Optional[str] = Field(None, pattern="^(available|partially_sold|reserved|sold)$")
    is_in_season: Optional[bool] = None
    user_role: Optional[str] = Field(None, pattern="^(agriculteur|collecteur|grossiste|transporteur)$")
    sort_by: Optional[str] = Field(None, pattern="^(created_at|price|quantity|rating)$")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

# Import circulaire différé
from app.schemas.user import UserResponse
ListingResponse.model_rebuild()
