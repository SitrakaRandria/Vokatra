# backend/app/main.py

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime

from app.config import settings
from app.api.v1 import auth, listings, offers, transporters, notifications
from app.api.websocket import chat
from app.core.database import db_manager
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.audit import AuditMiddleware
from app.middleware.csrf import CSRFMiddleware

# Configuration du logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Création de l'application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="API Vokatra - Plateforme agricole Madagascar",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ajout des middlewares de sécurité
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(AuditMiddleware)

# Gestionnaires d'erreurs
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    logger.warning(f"Erreur de validation: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Erreur de validation", "errors": errors}
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Erreur SQLAlchemy: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erreur interne de base de données"}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Une erreur interne est survenue"}
    )

# Inclusion des routeurs
app.include_router(auth.router, prefix="/api/v1")
app.include_router(listings.router, prefix="/api/v1")
app.include_router(offers.router, prefix="/api/v1")
app.include_router(transporters.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")

# Événements de démarrage/arrêt
@app.on_event("startup")
async def startup():
    logger.info("🚀 Démarrage de l'application Vokatra")
    try:
        await db_manager.initialize()
        logger.info("✅ Base de données initialisée avec succès")
    except Exception as e:
        logger.critical(f"❌ Échec de l'initialisation de la DB: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown():
    logger.info("🛑 Arrêt de l'application Vokatra")

# Route de santé
@app.get("/health", tags=["health"])
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

# Route racine
@app.get("/")
async def root():
    return {
        "message": "Bienvenue sur l'API Vokatra",
        "version": settings.VERSION,
        "docs": "/api/docs" if settings.DEBUG else None
    }
