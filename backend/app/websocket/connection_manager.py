"""
Gestionnaire des connexions WebSocket actives avec authentification.
"""
import asyncio
from typing import Dict, Set
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Gère les connexions WebSocket actives par utilisateur.
    Permet d'envoyer des messages à un utilisateur spécifique ou à tous.
    """
    def __init__(self):
        # Mapping user_id -> set of WebSocket connections (pour gérer plusieurs onglets)
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """Ajoute une connexion WebSocket pour un utilisateur."""
        await websocket.accept()
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connecté pour l'utilisateur {user_id} (total: {len(self.active_connections[user_id])})")

    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """Retire une connexion WebSocket."""
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        logger.info(f"WebSocket déconnecté pour l'utilisateur {user_id}")

    async def send_personal_message(self, message: dict, user_id: int) -> bool:
        """
        Envoie un message à toutes les connexions d'un utilisateur.
        Retourne True si au moins une connexion a reçu le message.
        """
        if user_id not in self.active_connections:
            return False

        message_str = json.dumps(message, default=str)
        sent = False
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_text(message_str)
                sent = True
            except Exception as e:
                logger.error(f"Erreur d'envoi WebSocket à l'utilisateur {user_id}: {e}")
        return sent

    async def broadcast(self, message: dict) -> None:
        """Diffuse un message à tous les utilisateurs connectés."""
        message_str = json.dumps(message, default=str)
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.error(f"Erreur de broadcast à l'utilisateur {user_id}: {e}")

# Instance unique
manager = ConnectionManager()
