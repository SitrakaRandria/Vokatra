"""
Schémas Pydantic pour le profil transporteur.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class TransporterProfileBase(BaseModel):
    """Schéma de base pour un profil transporteur."""
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True
    )

    coverage_region: List[str] = Field(
        default_factory=list,
        min_length=1,
        description="Régions couvertes"
    )
    vehicle_type: str = Field(..., min_length=2, max_length=50)
    capacity_kg: int = Field(..., gt=0, le=100000, description="Capacité en kg")
    base_rate: float = Field(..., ge=0, description="Tarif de base")
    rate_unit: str = Field(default="per_km", pattern="^(per_km|per_kg|per_trip)$")
    is_available: bool = True
    description: Optional[str] = Field(None, max_length=500)


class TransporterProfileCreate(TransporterProfileBase):
    """Schéma pour la création d'un profil transporteur."""
    pass


class TransporterProfileUpdate(BaseModel):
    """Schéma pour la mise à jour d'un profil transporteur."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    coverage_region: Optional[List[str]] = Field(None, min_length=1)
    vehicle_type: Optional[str] = Field(None, min_length=2, max_length=50)
    capacity_kg: Optional[int] = Field(None, gt=0, le=100000)
    base_rate: Optional[float] = Field(None, ge=0)
    rate_unit: Optional[str] = Field(None, pattern="^(per_km|per_kg|per_trip)$")
    is_available: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)


class TransporterProfileResponse(TransporterProfileBase):
    """Schéma de réponse pour un profil transporteur."""
    id: int
    user_id: int
