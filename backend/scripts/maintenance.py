"""
Scripts de maintenance pour la production.
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, update

from app.core.database import db_manager
from app.models.listing import Listing
from app.models.offer import Offer

async def cleanup_expired_offers():
    """Supprime les offres expirées."""
    async with db_manager.get_session() as session:
        cutoff = datetime.utcnow() - timedelta(days=7)
        stmt = select(Offer).where(
            Offer.status == 'pending',
            Offer.created_at < cutoff
        )
        result = await session.execute(stmt)
        expired_offers = result.scalars().all()
        
        for offer in expired_offers:
            offer.status = 'refused'
        
        await session.commit()
        print(f"✅ {len(expired_offers)} offres expirées marquées comme refusées")

async def update_seasonality_badges():
    """Met à jour les badges de saisonnalité pour toutes les annonces."""
    from app.core.seasonality import compute_seasonality_badge
    
    async with db_manager.get_session() as session:
        stmt = select(Listing)
        result = await session.execute(stmt)
        listings = result.scalars().all()
        
        current_month = datetime.utcnow().month
        updated = 0
        
        for listing in listings:
            is_in_season = await compute_seasonality_badge(
                product=listing.product,
                region=listing.region,
                current_month=current_month,
                session=session
            )
            if listing.is_in_season != is_in_season:
                listing.is_in_season = is_in_season
                updated += 1
        
        await session.commit()
        print(f"✅ {updated} annonces mises à jour")

if __name__ == "__main__":
    asyncio.run(cleanup_expired_offers())
    asyncio.run(update_seasonality_badges())
