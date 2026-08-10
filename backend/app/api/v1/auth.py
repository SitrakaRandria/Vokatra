"""
Endpoints d'authentification avec JWT et validation téléphone.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
import logging

from app.core.database import get_db_session
from app.core.auth import create_access_token, verify_password, get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserWithToken
from app.utils.validators import validate_phone_madagascar

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db_session)
) -> UserResponse:
    """
    Inscription d'un nouvel utilisateur avec validation du téléphone.
    
    Args:
        user_data: Données de l'utilisateur
        session: Session DB
        
    Returns:
        UserResponse: Utilisateur créé
        
    Raises:
        HTTPException: Si le téléphone existe déjà ou données invalides
    """
    try:
        # Vérification doublon de téléphone
        stmt = select(User).where(User.phone == user_data.phone)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            logger.warning(f"Tentative d'inscription avec téléphone existant: {user_data.phone}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce numéro de téléphone est déjà enregistré"
            )
        
        # Création de l'utilisateur
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            phone=user_data.phone,
            full_name=user_data.full_name,
            role=user_data.role,
            region=user_data.region,
            city=user_data.city,
            address=user_data.address,
            account_type=user_data.account_type,
            company_name=user_data.company_name,
            company_registration=user_data.company_registration,
            # Le mot de passe hashé sera stocké dans un champ séparé (à ajouter au modèle)
            # Pour l'instant on stocke dans un champ 'hashed_password' à ajouter
            hashed_password=hashed_password  # À ajouter dans le modèle User
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        logger.info(f"Nouvel utilisateur créé avec ID: {new_user.id}, téléphone: {new_user.phone}")
        return UserResponse.model_validate(new_user)
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur lors de l'inscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Une erreur est survenue lors de l'inscription"
        )

@router.post("/login", response_model=UserWithToken)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session)
) -> UserWithToken:
    """
    Connexion avec téléphone et mot de passe.
    
    Note: OAuth2PasswordRequestForm attend 'username', mais on utilise 'phone'.
    """
    try:
        # Recherche par téléphone
        stmt = select(User).where(User.phone == form_data.username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"Tentative de connexion avec téléphone inconnu: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Téléphone ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Vérification du mot de passe
        if not verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Mot de passe incorrect pour: {user.phone}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Téléphone ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Création du token
        access_token_expires = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "phone": user.phone, "role": user.role},
            expires_delta=access_token_expires
        )
        
        # Mise à jour de last_active
        user.last_active_at = datetime.utcnow()
        await session.commit()
        
        logger.info(f"Connexion réussie pour {user.phone}")
        return UserWithToken(
            **UserResponse.model_validate(user).model_dump(),
            access_token=access_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Erreur lors de la connexion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la connexion"
        )

@router.post("/verify-phone", response_model=dict)
async def verify_phone(
    phone: str,
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Vérification du numéro de téléphone (envoi de code SMS).
    Implémentation simplifiée - à connecter à un service SMS.
    """
    if not validate_phone_madagascar(phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Numéro de téléphone invalide"
        )
    
    # Ici, intégration avec service SMS (Twilio, etc.)
    # Pour le MVP, on simule un code
    verification_code = "123456"  # À remplacer par génération aléatoire
    
    # Stockage du code en base (à ajouter)
    logger.info(f"Code de vérification envoyé à {phone}: {verification_code}")
    
    return {
        "message": "Code de vérification envoyé",
        "phone": phone,
        "expires_in": 300  # 5 minutes
    }
