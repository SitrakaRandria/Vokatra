"""
Schémas Pydantic pour le modèle User avec validation stricte.
"""
from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic.types import StringConstraints
from typing_extensions import Annotated

from app.utils.validators import validate_phone_madagascar, normalize_phone

# Types personnalisés avec contraintes
PhoneStr = Annotated[
    str,
    StringConstraints(
        pattern=r'^\+261(20|30|32|33|34|38|39)\d{7}$',
        min_length=13,
        max_length=13
    )
]

class UserBase(BaseModel):
    """Schéma de base pour l'utilisateur."""
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True
    )
    
    phone: PhoneStr = Field(..., description="Numéro de téléphone malgache")
    full_name: str = Field(..., min_length=2, max_length=100, description="Nom complet")
    role: str = Field(..., pattern="^(agriculteur|collecteur|grossiste|transporteur)$")
    region: str = Field(..., min_length=2, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=200)
    account_type: str = Field(default="physical", pattern="^(physical|professional)$")
    
    # Pour les comptes professionnels
    company_name: Optional[str] = Field(None, max_length=200)
    company_registration: Optional[str] = Field(None, max_length=50)
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Valide et normalise le numéro de téléphone."""
        if not validate_phone_madagascar(v):
            raise ValueError("Format de téléphone invalide. Utilisez +261XXXXXXXXX")
        return normalize_phone(v) or v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Valide le rôle."""
        allowed = ['agriculteur', 'collecteur', 'grossiste', 'transporteur']
        if v not in allowed:
            raise ValueError(f"Rôle invalide. Choisissez parmi: {', '.join(allowed)}")
        return v

class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur."""
    password: str = Field(..., min_length=8, description="Mot de passe (min 8 caractères)")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Valide la complexité du mot de passe."""
        if len(v) < 8:
            raise ValueError("Le mot de passe doit faire au moins 8 caractères")
        if not any(c.isupper() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not any(c.islower() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not any(c.isdigit() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v

class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    region: Optional[str] = Field(None, min_length=2, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=200)
    company_name: Optional[str] = Field(None, max_length=200)
    company_registration: Optional[str] = Field(None, max_length=50)
    profile_picture: Optional[str] = Field(None, max_length=500)
    
    @field_validator('full_name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) < 2:
            raise ValueError("Le nom doit contenir au moins 2 caractères")
        return v

class UserVerificationDocuments(BaseModel):
    """Schéma pour les documents de vérification."""
    model_config = ConfigDict(extra="forbid")
    
    cin_url: str = Field(..., description="URL de la CIN")
    nif: Optional[str] = Field(None, max_length=20)
    carte_stat_url: Optional[str] = Field(None, description="URL de la carte statistique")
    
    @field_validator('cin_url', 'carte_stat_url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith(('http://', 'https://')):
            raise ValueError("L'URL doit commencer par http:// ou https://")
        return v

class UserResponse(UserBase):
    """Schéma de réponse pour l'utilisateur (sans données sensibles)."""
    id: int
    phone_verified: bool = False
    verification_status: str = "base"
    rating: Decimal = Field(default=Decimal('0.00'), ge=0, le=5)
    total_transactions: int = Field(default=0, ge=0)
    profile_picture: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_active_at: Optional[datetime] = None
    
    # Champs supplémentaires (selon rôle)
    transporter_profile: Optional['TransporterProfileResponse'] = None
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 5:
            raise ValueError("La note doit être comprise entre 0 et 5")
        return v

class UserWithToken(UserResponse):
    """Schéma de réponse avec token JWT."""
    access_token: str
    token_type: str = "bearer"

# Import différé pour éviter circularité
from app.schemas.transporter import TransporterProfileResponse
UserResponse.model_rebuild()
