"""
Schémas Pydantic pour les messages de chat.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class MessageCreate(BaseModel):
    """Schéma pour l'envoi d'un message via WebSocket."""
    model_config = ConfigDict(extra="forbid")

    conversation_id: int = Field(..., gt=0)
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    """Schéma de réponse pour un message."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_id: int
    content: str
    read: bool = False
    created_at: datetime
