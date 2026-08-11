"""
Service de notifications push avec Firebase Cloud Messaging.
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.models.notification_token import NotificationToken  # Nouveau modèle

logger = logging.getLogger(__name__)

class NotificationService:
    """Service pour gérer les notifications push."""
    
    FCM_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    
    def __init__(self):
        self.api_key = settings.FCM_SERVER_KEY
        self.project_id = settings.FCM_PROJECT_ID
        self.sender_id = settings.FCM_SENDER_ID
        self._client = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """Récupère ou crée un client HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._client
    
    async def send_push_notification(
        self,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """
        Envoie une notification push à un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur destinataire
            title: Titre de la notification
            body: Corps de la notification
            data: Données supplémentaires (URL, ID, etc.)
            session: Session DB optionnelle
            
        Returns:
            bool: True si la notification a été envoyée avec succès
        """
        if not self.api_key or not self.project_id:
            logger.warning("FCM non configuré, notification ignorée")
            return False
        
        try:
            # Récupérer les tokens de l'utilisateur
            if session is None:
                # Utiliser une session dédiée
                from app.core.database import db_manager
                async with db_manager.get_session() as db_session:
                    return await self._send_with_session(
                        user_id, title, body, data, db_session
                    )
            else:
                return await self._send_with_session(
                    user_id, title, body, data, session
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")
            return False
    
    async def _send_with_session(
        self,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]],
        session: AsyncSession
    ) -> bool:
        """Envoie la notification avec une session active."""
        
        # Récupérer les tokens de l'utilisateur
        stmt = select(NotificationToken).where(
            NotificationToken.user_id == user_id,
            NotificationToken.is_active == True
        )
        result = await session.execute(stmt)
        tokens = result.scalars().all()
        
        if not tokens:
            logger.info(f"Aucun token FCM actif pour l'utilisateur {user_id}")
            return False
        
        # Préparer le message
        message = {
            "message": {
                "notification": {
                    "title": title,
                    "body": body
                },
                "data": data or {},
                "android": {
                    "priority": "high",
                    "notification": {
                        "sound": "default",
                        "channel_id": "vokatra_channel"
                    }
                },
                "apns": {
                    "payload": {
                        "aps": {
                            "sound": "default",
                            "badge": 1
                        }
                    }
                },
                "webpush": {
                    "headers": {
                        "TTL": "86400"
                    },
                    "notification": {
                        "icon": "/icons/icon-192x192.png",
                        "badge": "/icons/badge-icon.png",
                        "requireInteraction": True,
                        "renotify": True
                    }
                }
            }
        }
        
        # Envoyer à chaque token
        success = False
        client = await self.get_client()
        
        for token in tokens:
            try:
                message["message"]["token"] = token.token
                response = await client.post(
                    self.FCM_URL.format(project_id=self.project_id),
                    json=message
                )
                
                if response.status_code == 200:
                    success = True
                    logger.info(f"Notification envoyée au token {token.id}")
                elif response.status_code == 404:
                    # Token invalide ou expiré
                    token.is_active = False
                    token.last_error = "Token expiré"
                    await session.commit()
                    logger.warning(f"Token {token.id} marqué comme inactif (404)")
                else:
                    token.last_error = f"FCM Error: {response.status_code}"
                    logger.error(f"Erreur FCM {response.status_code}: {response.text}")
                    await session.commit()
                    
            except Exception as e:
                logger.error(f"Erreur d'envoi au token {token.id}: {str(e)}")
                token.last_error = str(e)[:255]
                await session.commit()
        
        return success
    
    async def send_offer_notification(
        self,
        user_id: int,
        offer_id: int,
        listing_title: str,
        status: str
    ):
        """Envoie une notification pour une offre."""
        status_messages = {
            "pending": "nouvelle offre",
            "accepted": "offre acceptée",
            "refused": "offre refusée",
            "counter_offer": "contre-offre reçue"
        }
        
        title = f"Offre {status_messages.get(status, 'mise à jour')}"
        body = f"Offre sur '{listing_title}': {status_messages.get(status, '')}"
        
        await self.send_push_notification(
            user_id=user_id,
            title=title,
            body=body,
            data={
                "type": "offer",
                "offer_id": str(offer_id),
                "status": status,
                "click_action": f"/offers/{offer_id}"
            }
        )
    
    async def send_message_notification(
        self,
        user_id: int,
        conversation_id: int,
        sender_name: str,
        message_preview: str
    ):
        """Envoie une notification pour un nouveau message."""
        await self.send_push_notification(
            user_id=user_id,
            title=f"Nouveau message de {sender_name}",
            body=message_preview[:100] + ("..." if len(message_preview) > 100 else ""),
            data={
                "type": "message",
                "conversation_id": str(conversation_id),
                "click_action": f"/chat/{conversation_id}"
            }
        )

# Instance unique
notification_service = NotificationService()
