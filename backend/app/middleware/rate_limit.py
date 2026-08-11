"""
Middleware de rate limiting pour prévenir les attaques par force brute.
"""
import time
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware pour limiter le nombre de requêtes par IP."""
    
    def __init__(self, app):
        super().__init__(app)
        # Configurations
        self.rate_limits = {
            "default": (60, 60),  # 60 requêtes par minute
            "auth": (5, 60),      # 5 tentatives par minute
            "api": (100, 60)      # 100 requêtes par minute
        }
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 300  # Nettoyage toutes les 5 minutes
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next):
        # Nettoyage périodique
        await self._cleanup_old_requests()
        
        # Identifier l'IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Déterminer le type de route
        route_type = self._get_route_type(request.url.path)
        limit, period = self.rate_limits.get(route_type, self.rate_limits["default"])
        
        # Vérifier le rate limit
        if not await self._check_rate_limit(client_ip, limit, period):
            logger.warning(f"Rate limit dépassé pour {client_ip} sur {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de requêtes. Veuillez réessayer plus tard."
            )
        
        # Continuer la requête
        response = await call_next(request)
        
        # Ajouter des headers de rate limit
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(
            limit - len([t for t in self.requests[f"{client_ip}:{request.url.path}"] 
                        if time.time() - t < period])
        )
        
        return response
    
    def _get_route_type(self, path: str) -> str:
        """Détermine le type de route pour le rate limiting."""
        if path.startswith("/api/v1/auth"):
            return "auth"
        elif path.startswith("/api/v1"):
            return "api"
        return "default"
    
    async def _check_rate_limit(self, client_ip: str, limit: int, period: int) -> bool:
        """Vérifie si le client a dépassé sa limite."""
        key = client_ip
        now = time.time()
        
        # Nettoyer les anciennes entrées
        self.requests[key] = [t for t in self.requests[key] if now - t < period]
        
        # Vérifier la limite
        if len(self.requests[key]) >= limit:
            return False
        
        # Ajouter la requête
        self.requests[key].append(now)
        return True
    
    async def _cleanup_old_requests(self):
        """Nettoie les requêtes trop anciennes."""
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            # Nettoyer toutes les entrées
            for key in list(self.requests.keys()):
                self.requests[key] = [t for t in self.requests[key] 
                                     if now - t < 3600]  # Garder 1 heure max
                if not self.requests[key]:
                    del self.requests[key]
            self.last_cleanup = now
