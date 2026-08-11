"""
Endpoints pour la gestion des offres et contre‑offres.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from app.core.database import get_db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.listing import Listing
from app.models.offer import Offer
from app.models.conversation import Conversation
from app.schemas.offer import OfferCreate, OfferResponse, CounterOfferCreate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/offers", tags=["offers"])

@router.post("/", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
async def create_offer(
    offer_data: OfferCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> OfferResponse:
    """
    Crée une offre sur une annonce.
    Vérifie la disponibilité, crée une conversation si nécessaire.
    """
    try:
        # 1. Récupérer l'annonce
        stmt = select(Listing).where(Listing.id == offer_data.listing_id)
        result = await session.execute(stmt)
        listing = result.scalar_one_or_none()
        if not listing:
            raise HTTPException(status_code=404, detail="Annonce non trouvée")

        # 2. Vérifier que l'annonce est disponible
        if listing.status not in ["available", "partially_sold"]:
            raise HTTPException(status_code=409, detail="Cette annonce n'est plus disponible")

        # 3. Vérifier que l'acheteur n'est pas le vendeur
        if listing.user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Vous ne pouvez pas faire d'offre sur votre propre annonce")

        # 4. Vérifier la quantité demandée
        if offer_data.quantity > listing.available_quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Quantité demandée ({offer_data.quantity}) dépasse la disponibilité ({listing.available_quantity})"
            )

        # 5. Créer l'offre
        new_offer = Offer(
            listing_id=listing.id,
            buyer_id=current_user.id,
            quantity=offer_data.quantity,
            proposed_price=offer_data.proposed_price,
            buyer_message=offer_data.buyer_message,
            status="pending"
        )
        session.add(new_offer)
        await session.flush()  # Pour obtenir l'ID

        # 6. Créer une conversation entre acheteur et vendeur si elle n'existe pas déjà
        # On cherche une conversation entre les deux utilisateurs
        conv_stmt = select(Conversation).where(
            ((Conversation.user1_id == current_user.id) & (Conversation.user2_id == listing.user_id)) |
            ((Conversation.user1_id == listing.user_id) & (Conversation.user2_id == current_user.id))
        )
        conv_result = await session.execute(conv_stmt)
        conversation = conv_result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                user1_id=min(current_user.id, listing.user_id),
                user2_id=max(current_user.id, listing.user_id)
            )
            session.add(conversation)
            await session.flush()

        # 7. Commit
        await session.commit()
        await session.refresh(new_offer)

        logger.info(f"Offre créée: {new_offer.id} par utilisateur {current_user.id} sur annonce {listing.id}")
        return OfferResponse.model_validate(new_offer)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur création offre: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création de l'offre")

@router.post("/{offer_id}/accept", response_model=OfferResponse)
async def accept_offer(
    offer_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> OfferResponse:
    """
    Accepte une offre (seul le vendeur peut accepter).
    Met à jour la disponibilité de l'annonce et crée une commande (Order) si nécessaire.
    """
    try:
        # Récupération de l'offre
        stmt = select(Offer).where(Offer.id == offer_id)
        result = await session.execute(stmt)
        offer = result.scalar_one_or_none()
        if not offer:
            raise HTTPException(status_code=404, detail="Offre non trouvée")

        # Vérifier que l'offre est en attente
        if offer.status != "pending":
            raise HTTPException(status_code=409, detail="Cette offre n'est plus en attente")

        # Vérifier que l'utilisateur est le vendeur de l'annonce
        listing = await session.get(Listing, offer.listing_id)
        if listing.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à accepter cette offre")

        # Mettre à jour l'offre
        offer.status = "accepted"
        await session.flush()

        # Réduire la quantité disponible
        listing.available_quantity -= offer.quantity
        if listing.available_quantity == 0:
            listing.status = "sold"
        elif listing.available_quantity < listing.total_quantity:
            listing.status = "partially_sold"

        # Créer une commande (Order) - on garde le modèle Order à implémenter
        # Pour le moment on le saute, on loggue
        logger.info(f"Offre {offer_id} acceptée, commande à créer prochainement")

        await session.commit()
        await session.refresh(offer)
        return OfferResponse.model_validate(offer)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur acceptation offre: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'acceptation de l'offre")

@router.post("/{offer_id}/refuse", response_model=OfferResponse)
async def refuse_offer(
    offer_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> OfferResponse:
    """Refuse une offre (vendeur ou acheteur)."""
    try:
        stmt = select(Offer).where(Offer.id == offer_id)
        result = await session.execute(stmt)
        offer = result.scalar_one_or_none()
        if not offer:
            raise HTTPException(status_code=404, detail="Offre non trouvée")

        # Vérifier que l'utilisateur est soit le vendeur, soit l'acheteur
        listing = await session.get(Listing, offer.listing_id)
        if current_user.id not in (offer.buyer_id, listing.user_id):
            raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à refuser cette offre")

        if offer.status != "pending":
            raise HTTPException(status_code=409, detail="Cette offre n'est plus en attente")

        offer.status = "refused"
        await session.commit()
        await session.refresh(offer)
        return OfferResponse.model_validate(offer)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur refus offre: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors du refus de l'offre")

@router.post("/{offer_id}/counter", response_model=OfferResponse)
async def counter_offer(
    offer_id: int,
    counter_data: CounterOfferCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> OfferResponse:
    """Propose une contre‑offre (seul le vendeur peut faire une contre‑offre)."""
    try:
        stmt = select(Offer).where(Offer.id == offer_id)
        result = await session.execute(stmt)
        offer = result.scalar_one_or_none()
        if not offer:
            raise HTTPException(status_code=404, detail="Offre non trouvée")

        if offer.status != "pending":
            raise HTTPException(status_code=409, detail="Cette offre n'est plus en attente")

        listing = await session.get(Listing, offer.listing_id)
        if listing.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Seul le vendeur peut faire une contre‑offre")

        # Vérifier que la contre‑offre est valide
        if counter_data.counter_offer_quantity > listing.available_quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Quantité proposée ({counter_data.counter_offer_quantity}) dépasse la disponibilité ({listing.available_quantity})"
            )

        offer.status = "counter_offer"
        offer.counter_offer_price = counter_data.counter_offer_price
        offer.counter_offer_quantity = counter_data.counter_offer_quantity
        offer.seller_response = counter_data.seller_response

        await session.commit()
        await session.refresh(offer)
        return OfferResponse.model_validate(offer)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur contre‑offre: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création de la contre‑offre")
