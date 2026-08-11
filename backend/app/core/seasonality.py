"""
Calcul automatique du badge de saisonnalité.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.seasonality import Seasonality

logger = logging.getLogger(__name__)

async def compute_seasonality_badge(
    product: str,
    region: str,
    current_month: int,
    session: AsyncSession
) -> bool:
    """
    Calcule si un produit est en saison dans une région donnée.
    
    Args:
        product: Nom du produit
        region: Région
        current_month: Mois actuel (1-12)
        session: Session DB
        
    Returns:
        bool: True si en saison
    """
    try:
        # Recherche de la saisonnalité pour ce produit/région
        stmt = select(Seasonality).where(
            Seasonality.product == product,
            Seasonality.region == region
        )
        result = await session.execute(stmt)
        season = result.scalar_one_or_none()
        
        if not season:
            logger.debug(f"Aucune saisonnalité définie pour {product} dans {region}")
            return False
        
        # Vérification si le mois courant est dans l'intervalle
        # Gestion des saisons qui chevauchent une année (ex: novembre à février)
        if season.month_start <= season.month_end:
            # Cas normal: même année
            is_in_season = season.month_start <= current_month <= season.month_end
        else:
            # Cas chevauchant: par ex novembre à février
            is_in_season = current_month >= season.month_start or current_month <= season.month_end
        
        logger.debug(f"Saisonnalité pour {product} dans {region}: {is_in_season}")
        return is_in_season
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul de saisonnalité pour {product} dans {region}: {str(e)}")
        # En cas d'erreur, on retourne False par défaut (sécurité)
        return False
