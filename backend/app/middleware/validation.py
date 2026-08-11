"""
Middleware et décorateurs pour la validation avancée.
"""
from functools import wraps
from typing import Type, Any
from fastapi import HTTPException, status, Request
from pydantic import BaseModel, ValidationError
import re

class Validators:
    """Collection de validateurs réutilisables."""
    
    @staticmethod
    def validate_malagasy_phone(phone: str) -> bool:
        """Valide un numéro de téléphone malgache."""
        pattern = r'^\+261(20|30|32|33|34|38|39)\d{7}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def validate_positive_amount(amount: float) -> bool:
        """Valide qu'un montant est positif."""
        return amount > 0
    
    @staticmethod
    def validate_price(price: float) -> bool:
        """Valide qu'un prix est valide (pas de négatif)."""
        return price >= 0
    
    @staticmethod
    def validate_quantity(quantity: float) -> bool:
        """Valide qu'une quantité est valide."""
        return quantity > 0
    
    @staticmethod
    def validate_region(region: str) -> bool:
        """Valide qu'une région est dans la liste autorisée."""
        allowed_regions = [
            "Analamanga", "Atsinanana", "Diana", "Sava", "Betsiboka",
            "Boeny", "Melaky", "Menabe", "Haute Matsiatra", "Vatovavy",
            "Vakinankaratra", "Ihorombe", "Androy", "Anosy", "Atsimo-Andrefana",
            "Atsimo-Atsinanana", "Analanjirofo", "Amoron'i Mania", "Sofia",
            "Itasy", "Bongolava", "Fitovinany", "Tolagnaro"
        ]
        return region in allowed_regions

def validate_body(schema: Type[BaseModel]):
    """Décorateur pour valider le corps de la requête avec Pydantic."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                body = await request.json()
                validated_data = schema(**body)
                return await func(request, validated_data, *args, **kwargs)
            except ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=e.errors()
                )
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
