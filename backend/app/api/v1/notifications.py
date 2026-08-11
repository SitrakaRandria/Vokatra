"""
Endpoints pour la gestion des notifications push.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.core.database import get_db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.notification_token import NotificationToken

router = APIRouter(prefix="/notifications", tags=["notifications"])

class TokenRegistration(BaseModel):
    token: str = Field(..., max_length=500)
    device_type: str = Field(..., pattern="^(web|ios|android)$")
    device_id: Optional[str] = Field(None, max_length=200)

@router.post("/register-token", status_code=status.HTTP_201_CREATED)
async def register_token(
    registration: TokenRegistration,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Enregistre ou met à jour un token FCM pour l'utilisateur.
    """
    try:
        # Vérifier si le token existe déjà
        stmt = select(NotificationToken).where(NotificationToken.token == registration.token)
        result = await session.execute(stmt)
        existing_token = result.scalar_one_or_none()
        
        if existing_token:
            # Mettre à jour le token existant
            existing_token.user_id = current_user.id
            existing_token.device_type = registration.device_type
            existing_token.device_id = registration.device_id
            existing_token.is_active = True
            existing_token.last_used_at = datetime.utcnow()
            existing_token.last_error = None
            await session.commit()
            return {"message": "Token mis à jour avec succès"}
        
        # Créer un nouveau token
        new_token = NotificationToken(
            user_id=current_user.id,
            token=registration.token,
            device_type=registration.device_type,
            device_id=registration.device_id,
            is_active=True,
            last_used_at=datetime.utcnow()
        )
        session.add(new_token)
        await session.commit()
        
        logger.info(f"Nouveau token FCM enregistré pour l'utilisateur {current_user.id}")
        return {"message": "Token enregistré avec succès"}
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur lors de l'enregistrement du token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'enregistrement du token"
        )

@router.delete("/unregister-token")
async def unregister_token(
    token: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Désenregistre un token (déconnexion, désactivation).
    """
    try:
        stmt = select(NotificationToken).where(
            NotificationToken.token == token,
            NotificationToken.user_id == current_user.id
        )
        result = await session.execute(stmt)
        token_obj = result.scalar_one_or_none()
        
        if token_obj:
            token_obj.is_active = False
            await session.commit()
            logger.info(f"Token {token_obj.id} désactivé")
        
        return {"message": "Token désenregistré avec succès"}
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur lors du désenregistrement du token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du désenregistrement du token"
        )
