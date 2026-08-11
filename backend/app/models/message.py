"""
Modèle Message pour les échanges dans une conversation.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Integer, DateTime, Text, ForeignKey, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.conversation import Conversation

class Message(Base):
    """Message individuel dans une conversation."""
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_message_conversation", "conversation_id"),
        Index("idx_message_sender", "sender_id"),
        Index("idx_message_created", "created_at"),
        Index("idx_message_read", "read"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relations
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id], lazy="selectin")
