"""
Endpoints CRUD pour les annonces avec gestion de saisonnalité automatique.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from typing import Optional, List
from datetime import datetime
import logging

from app.core.database import get_db_session
from app.core.auth import get_current_user
from app.core.seasonality import compute_seasonality_badge
from app.models.user import User
from app.models.listing import Listing
from app.schemas.listing import (
    ListingCreate, ListingUpdate, ListingResponse, ListingFilterParams
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/listings", tags=["listings"])

@router.post("/", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(
    listing_data: ListingCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> ListingResponse:
    """
    Crée une nouvelle annonce pour l'utilisateur connecté.
    Calcule automatiquement le badge de saisonnalité.
    """
    try:
        # Vérification des données de saisonnalité
        current_month = datetime.utcnow().month
        is_in_season = compute_seasonality_badge(
            product=listing_data.product,
            region=listing_data.region,
            current_month=current_month,
            session=session
        )
        
        # Création de l'annonce
        new_listing = Listing(
            user_id=current_user.id,
            product=listing_data.product,
            description=listing_data.description,
            total_quantity=listing_data.total_quantity,
            available_quantity=listing_data.total_quantity,  # Initialement identique
            unit=listing_data.unit,
            price=listing_data.price,
            price_mode=listing_data.price_mode,
            region=listing_data.region,
            location_detail=listing_data.location_detail,
            availability_date=listing_data.availability_date,
            photos=listing_data.photos or [],
            is_in_season=is_in_season,
            status="available",
            # Les mois de saison seront renseignés par le compute_seasonality_badge
        )
        
        session.add(new_listing)
        await session.commit()
        await session.refresh(new_listing)
        
        # Chargement de l'utilisateur associé
        await session.refresh(new_listing, attribute_names=['user'])
        
        logger.info(f"Nouvelle annonce créée par l'utilisateur {current_user.id}: {new_listing.id}")
        return ListingResponse.model_validate(new_listing)
        
    except ValueError as e:
        await session.rollback()
        logger.warning(f"Erreur de validation pour l'annonce: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur lors de la création de l'annonce: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de l'annonce"
        )

@router.get("/", response_model=List[ListingResponse])
async def get_listings(
    filters: ListingFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session)
) -> List[ListingResponse]:
    """
    Récupère les annonces avec filtres avancés.
    """
    try:
        # Construction de la requête de base
        query = select(Listing).where(Listing.status.in_(['available', 'partially_sold']))
        
        # Filtres
        if filters.product:
            query = query.where(Listing.product.ilike(f"%{filters.product}%"))
        if filters.region:
            query = query.where(Listing.region == filters.region)
        if filters.min_price is not None:
            query = query.where(Listing.price >= filters.min_price)
        if filters.max_price is not None:
            query = query.where(Listing.price <= filters.max_price)
        if filters.min_quantity is not None:
            query = query.where(Listing.available_quantity >= filters.min_quantity)
        if filters.status:
            query = query.where(Listing.status == filters.status)
        if filters.is_in_season is not None:
            query = query.where(Listing.is_in_season == filters.is_in_season)
        if filters.user_role:
            query = query.join(Listing.user).where(User.role == filters.user_role)
        
        # Tri
        sort_field = getattr(Listing, filters.sort_by, Listing.created_at)
        if filters.sort_order == "asc":
            query = query.order_by(asc(sort_field))
        else:
            query = query.order_by(desc(sort_field))
        
        # Pagination
        query = query.offset(filters.offset).limit(filters.limit)
        
        # Exécution
        result = await session.execute(query)
        listings = result.scalars().all()
        
        # Chargement des relations (évite N+1)
        for listing in listings:
            await session.refresh(listing, attribute_names=['user'])
        
        return [ListingResponse.model_validate(l) for l in listings]
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des annonces: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des annonces"
        )

@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: int,
    session: AsyncSession = Depends(get_db_session)
) -> ListingResponse:
    """
    Récupère une annonce par son ID avec tous les détails.
    """
    try:
        stmt = select(Listing).where(Listing.id == listing_id)
        result = await session.execute(stmt)
        listing = result.scalar_one_or_none()
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annonce non trouvée"
            )
        
        await session.refresh(listing, attribute_names=['user', 'offers'])
        return ListingResponse.model_validate(listing)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'annonce {listing_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'annonce"
        )

@router.put("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: int,
    update_data: ListingUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> ListingResponse:
    """
    Met à jour une annonce existante (seul le propriétaire peut modifier).
    """
    try:
        # Récupération de l'annonce
        stmt = select(Listing).where(Listing.id == listing_id)
        result = await session.execute(stmt)
        listing = result.scalar_one_or_none()
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annonce non trouvée"
            )
        
        # Vérification des droits
        if listing.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas autorisé à modifier cette annonce"
            )
        
        # Mise à jour des champs
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(listing, key, value)
        
        # Recalcul de la saisonnalité si produit ou région changent
        if 'product' in update_dict or 'region' in update_dict:
            current_month = datetime.utcnow().month
            listing.is_in_season = compute_seasonality_badge(
                product=listing.product,
                region=listing.region,
                current_month=current_month,
                session=session
            )
        
        listing.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(listing)
        await session.refresh(listing, attribute_names=['user'])
        
        logger.info(f"Annonce {listing_id} mise à jour par l'utilisateur {current_user.id}")
        return ListingResponse.model_validate(listing)
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur lors de la mise à jour de l'annonce {listing_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour de l'annonce"
        )

@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> None:
    """
    Supprime une annonce (soft delete à implémenter si besoin).
    """
    try:
        stmt = select(Listing).where(Listing.id == listing_id)
        result = await session.execute(stmt)
        listing = result.scalar_one_or_none()
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annonce non trouvée"
            )
        
        if listing.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas autorisé à supprimer cette annonce"
            )
        
        # Vérifier si des offres en cours existent
        if listing.offers:
            active_offers = [o for o in listing.offers if o.status in ['pending', 'counter_offer']]
            if active_offers:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Impossible de supprimer une annonce avec des offres actives"
                )
        
        await session.delete(listing)
        await session.commit()
        
        logger.info(f"Annonce {listing_id} supprimée par l'utilisateur {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur lors de la suppression de l'annonce {listing_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression de l'annonce"
        )
