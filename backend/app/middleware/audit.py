"""
Middleware pour logger toutes les actions importantes.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import json
import logging
from datetime import datetime

from app.models.audit_log import AuditLog
from app.core.database import db_manager

logger = logging.getLogger(__name__)

class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware qui logge toutes les requêtes modifiant des données."""
    
    MODIFY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Logger seulement les requêtes de modification
        if request.method in self.MODIFY_METHODS:
            await self._log_audit(request, response)
        
        return response
    
    async def _log_audit(self, request: Request, response):
        """Logge l'action dans la base de données."""
        try:
            # Récupérer l'utilisateur depuis le token (si présent)
            user_id = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    from app.core.auth import verify_token
                    payload = verify_token(token)
                    user_id = int(payload.get("sub"))
                except Exception:
                    pass
            
            # Créer le log d'audit
            audit_log = AuditLog(
                user_id=user_id,
                action=request.method,
                resource_type=request.url.path.split("/")[-1] or "unknown",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "query_params": str(request.query_params),
                }
            )
            
            # Enregistrer de manière asynchrone
            async with db_manager.get_session() as session:
                session.add(audit_log)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Erreur lors de l'audit: {str(e)}")
