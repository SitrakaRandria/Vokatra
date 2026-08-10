"""
Configuration centralisée avec validation Pydantic.
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator, ValidationError
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Configuration de l'application avec validation stricte."""
    
    # Application
    APP_NAME: str = "Vokatra API"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="Mode debug")
    ENVIRONMENT: str = Field(default="development", description="Environnement: development/production/test")
    
    # Base de données
    DATABASE_URL: str = Field(..., description="URL de connexion PostgreSQL")
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=50, description="Taille du pool de connexions")
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, description="Overflow max du pool")
    
    # JWT
    JWT_SECRET_KEY: str = Field(..., min_length=32, description="Clé secrète JWT (min 32 caractères)")
    JWT_ALGORITHM: str = Field(default="HS256", description="Algorithme JWT")
    JWT_EXPIRATION_MINUTES: int = Field(default=1440, gt=0, description="Expiration JWT en minutes")
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = Field(..., description="Nom du cloud Cloudinary")
    CLOUDINARY_API_KEY: str = Field(..., description="Clé API Cloudinary")
    CLOUDINARY_API_SECRET: str = Field(..., description="Secret API Cloudinary")
    
    # Firebase Cloud Messaging
    FCM_SERVER_KEY: Optional[str] = Field(None, description="Clé serveur FCM pour notifications push")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "https://vokatra.mg"],
        description="Origines autorisées pour CORS"
    )
    
    # Internationalisation
    SUPPORTED_LANGUAGES: List[str] = Field(default=["fr", "mg"], description="Langues supportées")
    DEFAULT_LANGUAGE: str = Field(default="fr", description="Langue par défaut")
    
    @validator('DATABASE_URL')
    def validate_database_url(cls, v: str) -> str:
        """Valide que l'URL de base de données est correcte."""
        if not v.startswith(('postgresql://', 'postgresql+asyncpg://')):
            raise ValueError("DATABASE_URL doit être une URL PostgreSQL valide (postgresql:// ou postgresql+asyncpg://)")
        if 'postgresql+asyncpg://' not in v and not v.startswith('postgresql://'):
            # Ajoute automatiquement asyncpg si manquant
            v = v.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return v
    
    @validator('JWT_SECRET_KEY')
    def validate_jwt_secret(cls, v: str) -> str:
        """Valide que la clé JWT est suffisamment sécurisée."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY doit faire au moins 32 caractères")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignorer les variables inattendues

# Instanciation des settings avec gestion d'erreur
try:
    settings = Settings()
except ValidationError as e:
    logger.critical(f"Erreur de configuration: {e}")
    raise RuntimeError(f"Configuration invalide: {e}")
