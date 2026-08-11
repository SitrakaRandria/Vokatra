"""
Schémas Pydantic pour l'historique des prix.
"""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PriceHistoryResponse(BaseModel):
    """Schéma de réponse pour une entrée d'historique de prix."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: str
    region: str
    avg_price: Decimal
    min_price: Decimal
    max_price: Decimal
    transaction_count: int = Field(default=0, ge=0)
    month_year: datetime
    created_at: datetime
    updated_at: datetime

    @field_validator('max_price')
    @classmethod
    def validate_price_range(cls, v: Decimal, info) -> Decimal:
        """Valide la cohérence min <= avg <= max."""
        min_price = info.data.get('min_price')
        avg_price = info.data.get('avg_price')
        if min_price is not None and v < min_price:
            raise ValueError("max_price ne peut pas être inférieur à min_price")
        if avg_price is not None and v < avg_price:
            raise ValueError("max_price ne peut pas être inférieur à avg_price")
        return v
