"""
Configuration de la base de données avec gestion robuste des erreurs et rollback automatique.
"""
import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    async_sessionmaker, 
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import event, exc
from sqlalchemy.pool import NullPool

from app.config import settings

# Configuration du logging
logger = logging.getLogger(__name__)

# Base pour les modèles SQLAlchemy
Base = declarative_base()

class DatabaseManager:
    """
    Gestionnaire de base de données asynchrone avec rollback automatique en cas d'erreur.
    """
    _instance: Optional['DatabaseManager'] = None
    _engine: Optional[AsyncEngine] = None
    _async_session_maker: Optional[async_sessionmaker] = None
    
    def __new__(cls) -> 'DatabaseManager':
        """Singleton pattern pour éviter multiples connexions DB."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialisation du gestionnaire avec validation des paramètres."""
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # Validation des paramètres critiques
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL non configurée dans les variables d'environnement")
        
        logger.info("Initialisation du gestionnaire de base de données")
    
    async def initialize(self) -> None:
        """
        Crée le moteur de base de données et la session maker.
        Gère les erreurs de connexion avec retry automatique.
        """
        try:
            # Configuration du moteur avec gestion des pools
            self._engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_pre_ping=True,  # Vérification de connexion avant utilisation
                pool_recycle=3600,   # Recyclage des connexions anciennes
                poolclass=NullPool if settings.ENVIRONMENT == "test" else None
            )
            
            # Création du session maker
            self._async_session_maker = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
            
            logger.info("Moteur de base de données initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur critique lors de l'initialisation de la DB: {str(e)}")
            raise RuntimeError(f"Impossible de se connecter à la base de données: {e}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Fournit une session de base de données avec rollback automatique en cas d'erreur.
        
        Yields:
            AsyncSession: Session SQLAlchemy asynchrone
            
        Raises:
            Exception: Toute exception est propagée après rollback
        """
        if not self._async_session_maker:
            await self.initialize()
        
        session: AsyncSession = self._async_session_maker()
        try:
            yield session
            # Commit automatique si aucune erreur
            await session.commit()
        except (exc.SQLAlchemyError, Exception) as e:
            # Rollback systématique pour toute erreur
            try:
                await session.rollback()
                logger.error(f"Rollback effectué suite à une erreur: {str(e)}")
            except Exception as rollback_error:
                logger.error(f"Erreur lors du rollback: {str(rollback_error)}")
            # Propagation de l'erreur originale
            raise
        finally:
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Erreur lors de la fermeture de la session: {str(e)}")

# Instance globale du gestionnaire
db_manager = DatabaseManager()

# Fonction d'injection de dépendance pour FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI pour obtenir une session DB."""
    async with db_manager.get_session() as session:
        yield session
