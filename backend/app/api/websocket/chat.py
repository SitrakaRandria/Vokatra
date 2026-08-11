"""
Endpoint WebSocket pour le chat en temps réel.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import logging

from app.core.database import get_db_session
from app.core.auth import verify_token
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.websocket.connection_manager import manager
from app.schemas.message import MessageCreate, MessageResponse  # À créer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

@router.websocket("/ws/{token}")
async def websocket_chat(
    websocket: WebSocket,
    token: str,
):
    """
    Endpoint WebSocket pour le chat.
    L'URL doit être : ws://.../api/v1/chat/ws/{jwt_token}
    """
    # 1. Authentification via le token JWT
    try:
        payload = verify_token(token)
        user_id = int(payload.get("sub"))
    except Exception as e:
        logger.error(f"Échec d'authentification WebSocket: {e}")
        await websocket.close(code=1008, reason="Token invalide")
        return

    # 2. Récupération de la session DB
    async for db_session in get_db_session():
        try:
            # Vérifier que l'utilisateur existe
            stmt = select(User).where(User.id == user_id)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                await websocket.close(code=1008, reason="Utilisateur introuvable")
                return

            # 3. Ajout à la liste des connexions
            await manager.connect(websocket, user_id)

            # 4. Boucle de réception des messages
            while True:
                try:
                    data = await websocket.receive_text()
                    message_data = json.loads(data)

                    # Valider le contenu (type d'action)
                    action = message_data.get("action")
                    if action == "send_message":
                        await handle_send_message(db_session, user_id, message_data, websocket)
                    elif action == "mark_read":
                        await handle_mark_read(db_session, user_id, message_data)
                    else:
                        await websocket.send_text(json.dumps({"error": "Action non reconnue"}))

                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({"error": "Format JSON invalide"}))
                except Exception as e:
                    logger.error(f"Erreur dans la boucle WebSocket: {e}")
                    await websocket.send_text(json.dumps({"error": str(e)}))

        finally:
            # 5. Nettoyage
            await manager.disconnect(websocket, user_id)
            break  # Sortir du générateur de session

# Handlers internes
async def handle_send_message(db_session: AsyncSession, sender_id: int, data: dict, websocket: WebSocket):
    """Traite l'envoi d'un message."""
    # Extraction des données
    conversation_id = data.get("conversation_id")
    content = data.get("content", "").strip()
    if not content:
        await websocket.send_text(json.dumps({"error": "Le message ne peut pas être vide"}))
        return

    # Récupération de la conversation
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db_session.execute(stmt)
    conversation = result.scalar_one_or_none()
    if not conversation:
        await websocket.send_text(json.dumps({"error": "Conversation introuvable"}))
        return

    # Vérifier que l'utilisateur fait partie de la conversation
    if sender_id not in (conversation.user1_id, conversation.user2_id):
        await websocket.send_text(json.dumps({"error": "Vous n'êtes pas autorisé dans cette conversation"}))
        return

    # Créer le message
    new_message = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
        read=False
    )
    db_session.add(new_message)
    conversation.updated_at = datetime.utcnow()
    await db_session.commit()
    await db_session.refresh(new_message)

    # Préparer la réponse (contenant le message envoyé)
    response = {
        "action": "new_message",
        "message": {
            "id": new_message.id,
            "sender_id": new_message.sender_id,
            "conversation_id": new_message.conversation_id,
            "content": new_message.content,
            "created_at": new_message.created_at.isoformat(),
            "read": new_message.read
        }
    }

    # Envoyer au sender (confirmation)
    await websocket.send_text(json.dumps(response))

    # Envoyer au destinataire (l'autre utilisateur de la conversation)
    recipient_id = conversation.user2_id if conversation.user1_id == sender_id else conversation.user1_id
    await manager.send_personal_message(response, recipient_id)

async def handle_mark_read(db_session: AsyncSession, user_id: int, data: dict):
    """Marque un message comme lu."""
    message_id = data.get("message_id")
    if not message_id:
        return

    stmt = select(Message).where(Message.id == message_id)
    result = await db_session.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        return

    # Vérifier que l'utilisateur est bien le destinataire du message (pas l'expéditeur)
    # Et que le message appartient à une conversation dont il fait partie
    if message.sender_id == user_id:
        return  # On ne peut pas marquer ses propres messages comme lus

    # Vérifier la conversation
    conv_stmt = select(Conversation).where(Conversation.id == message.conversation_id)
    conv_result = await db_session.execute(conv_stmt)
    conv = conv_result.scalar_one_or_none()
    if not conv or user_id not in (conv.user1_id, conv.user2_id):
        return

    message.read = True
    await db_session.commit()
