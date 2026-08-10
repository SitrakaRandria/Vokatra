"""
Fonctions d'authentification JWT avec gestion d'erreurs robuste.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext

from app.config import settings
from app.models.user import User
from app.core.database import get_db_session
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Crée un token JWT d'accès.
    
    Args:
        data: Données à encoder (doit contenir 'sub' avec l'ID utilisateur)
        expires_delta: Durée de validité (défaut: settings.JWT_EXPIRATION_MINUTES)
        
    Returns:
        str: Token JWT
        
    Raises:
        ValueError: Si 'sub' est manquant
    """
    if "sub" not in data:
        raise ValueError("La clé 'sub' est requise dans les données du token")
    
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRATION_MINUTES))
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Erreur lors de la création du token JWT: {str(e)}")
        raise RuntimeError("Impossible de créer le token d'authentification")

def verify_token(token: str) -> Dict[str, Any]:
    """
    Vérifie et décode un token JWT.
    
    Args:
        token: Token JWT
        
    Returns:
        Dict[str, Any]: Payload décodé
        
    Raises:
        HTTPException: Si le token est invalide ou expiré
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token JWT expiré")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée, veuillez vous reconnecter",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.JWTError as e:
        logger.warning(f"Token JWT invalide: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification invalide",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Erreur inattendue lors du décodage du token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la vérification du token"
        )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Récupère l'utilisateur courant à partir du token JWT.
    
    Returns:
        User: Utilisateur authentifié
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas trouvé ou token invalide
    """
    try:
        payload = verify_token(token)
        user_id_str = payload.get("sub")
        
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide: identifiant utilisateur manquant",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        try:
            user_id = int(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide: identifiant utilisateur mal formé",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Recherche de l'utilisateur
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Vérification supplémentaire: téléphone correspondant (optionnel)
        phone_from_token = payload.get("phone")
        if phone_from_token and user.phone != phone_from_token:
            logger.warning(f"Incohérence entre token et utilisateur: {user.phone} vs {phone_from_token}")
            # On ne bloque pas, mais on loggue
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'utilisateur: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de l'authentification"
        )

def get_password_hash(password: str) -> str:
    """
    Hash un mot de passe avec bcrypt.
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Erreur lors du hachage du mot de passe: {str(e)}")
        raise RuntimeError("Erreur interne lors du hachage du mot de passe")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie un mot de passe en clair contre son hash.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du mot de passe: {str(e)}")
        return False
