"""
Middleware de protection CSRF.
"""
import secrets
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware pour protéger contre les attaques CSRF."""
    
    EXEMPT_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/verify-phone",
        "/health",
        "/api/docs",
        "/api/redoc"
    }
    
    async def dispatch(self, request: Request, call_next):
        # Vérifier si le path est exempté
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Pour les méthodes non-safe (POST, PUT, DELETE, PATCH)
        if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
            # Vérifier le token CSRF
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token manquant"
                )
            
            # Vérifier le token stocké en session
            session_token = request.cookies.get("csrf_token")
            if not session_token or not secrets.compare_digest(csrf_token, session_token):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token invalide"
                )
        
        response = await call_next(request)
        
        # Générer un nouveau token CSRF pour la réponse
        if request.method == "GET":
            new_token = secrets.token_urlsafe(32)
            response.set_cookie(
                key="csrf_token",
                value=new_token,
                httponly=True,
                secure=settings.ENVIRONMENT == "production",
                samesite="strict",
                max_age=3600  # 1 heure
            )
        
        return response
